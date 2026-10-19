"""Test-only resource metadata/process readers; no inference or network."""

import json
import socket
import threading
from contextlib import contextmanager
from types import SimpleNamespace
from urllib.request import ProxyHandler

import pytest

from tracetrail import cli, resources

MODEL = "test-only-local-model"


@pytest.fixture(autouse=True)
def network_forbidden(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("A resource test attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)


def loaded(**changes):
    return {
        "models": [
            {
                "model": MODEL,
                "digest": "test-only-digest",
                "size": 1000,
                "size_vram": 700,
                "context_length": 16384,
                **changes,
            }
        ]
    }


def rss():
    return {"available": True, **resources.process_tree_rss("10\n", "10 1 100\n11 10 50\n")}


def test_metadata_request_is_fixed_loopback_no_proxy_auth_or_redirect(monkeypatch):
    captured = {}
    monkeypatch.setenv("HTTP_PROXY", "http://example.invalid:3128")
    monkeypatch.setenv("OLLAMA_API_KEY", "test-only-ambient-key")

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            assert limit == 65537
            return json.dumps(loaded()).encode()

    class Opener:
        def open(self, request, timeout):
            captured.update(request=request, timeout=timeout)
            return Response()

    def opener(*handlers):
        captured["handlers"] = handlers
        return Opener()

    monkeypatch.setattr(resources, "build_opener", opener)
    assert resources._read_ollama_ps(0.5) == loaded()
    request = captured["request"]
    assert request.full_url == "http://127.0.0.1:11434/api/ps"
    assert request.get_method() == "GET"
    assert request.data is None
    assert request.get_header("Authorization") == "local-only-no-auth"
    assert "test-only-ambient-key" not in str(request.headers)
    assert captured["timeout"] == 0.5
    assert next(h for h in captured["handlers"] if isinstance(h, ProxyHandler)).proxies == {}
    redirect = next(h for h in captured["handlers"] if isinstance(h, resources._NoRedirect))
    with pytest.raises(ValueError, match="cannot redirect"):
        redirect.redirect_request(request, None, 307, "redirect", {}, "https://example.invalid")


@pytest.mark.parametrize("value", [b"x" * 65537, b"[]", b'{"models":null}', b'{"models":[1]}'])
def test_invalid_or_oversized_api_response_rejected(monkeypatch, value):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            return value

    monkeypatch.setattr(
        resources, "build_opener", lambda *args: SimpleNamespace(open=lambda *a, **kw: Response())
    )
    with pytest.raises(ValueError):
        resources._read_ollama_ps(0.5)


def test_api_reader_uses_total_subprocess_deadline_without_model_endpoint(monkeypatch):
    captured = {}

    def run(args, **kwargs):
        captured.update(args=args, **kwargs)
        return SimpleNamespace(returncode=0, stdout=json.dumps(loaded()).encode())

    monkeypatch.setattr(resources.subprocess, "run", run)
    assert resources.read_ollama_ps(0.5) == loaded()
    assert captured["args"][:3] == [resources.sys.executable, "-I", "-c"]
    assert "_read_ollama_ps" in captured["args"][3]
    assert "/api/generate" not in captured["args"][3]
    assert "/api/chat" not in captured["args"][3]
    assert captured["args"][4] == "0.5"
    assert captured["timeout"] == 0.5
    assert captured["capture_output"] is True
    assert captured["check"] is False


def test_total_reader_timeout_becomes_bounded_capture_error(monkeypatch):
    def timeout(*args, **kwargs):
        raise resources.subprocess.TimeoutExpired("test-only-reader", 0.05)

    monkeypatch.setattr(resources.subprocess, "run", timeout)
    monkeypatch.setattr(resources, "read_process_rss", lambda timeout: rss())
    sampler = resources.ResourceSampler(MODEL, max_samples=1)
    sampler.start()
    report = sampler.stop()
    assert report["status"] == "partial"
    assert report["samples"][0]["errors"] == [{"source": "ollama", "error_type": "TimeoutExpired"}]


def test_process_rss_numeric_descendants_units_and_unrelated_processes():
    result = resources.process_tree_rss("10\n10\n", "10 1 100\n11 10 50\n12 11 25\n20 1 999999\n")
    assert result["listener_pids"] == [10]
    assert [row["pid"] for row in result["processes"]] == [10, 11, 12]
    assert result["processes"][0]["role"] == "listener"
    assert result["processes"][1]["role"] == "descendant"
    assert result["rss_sum_bytes"] == 175 * 1024
    assert result["tree_complete"] is True
    assert resources.process_tree_rss("", "10 1 100\n")["rss_sum_bytes"] is None


@pytest.mark.parametrize(
    "listeners,processes",
    [("bad\n", "10 1 100"), ("10", "10 1 -1"), ("10", "10 1 1\n10 1 2")],
)
def test_invalid_process_metadata_rejected(listeners, processes):
    with pytest.raises(ValueError):
        resources.process_tree_rss(listeners, processes)


def test_process_cap_is_disclosed_and_not_complete():
    result = resources.process_tree_rss(
        "1", "1 0 1\n" + "\n".join(f"{pid} 1 2" for pid in range(2, 71))
    )
    assert len(result["processes"]) == 64
    assert result["process_count"] == 70
    assert result["omitted_process_count"] == 6
    assert result["tree_complete"] is False


def test_process_commands_do_not_read_arguments_or_environment(monkeypatch):
    monkeypatch.setattr(resources.platform, "system", lambda: "Darwin")
    calls = []

    def command(args, timeout, max_bytes):
        calls.append((args, timeout, max_bytes))
        return "10\n" if args[0].endswith("lsof") else "10 1 100\n"

    monkeypatch.setattr(resources, "_command", command)
    assert resources.read_process_rss(0.5)["rss_sum_bytes"] == 102400
    assert calls[0] == (["/usr/sbin/lsof", "-nP", "-iTCP:11434", "-sTCP:LISTEN", "-t"], 0.5, 4096)
    assert calls[1] == (["/bin/ps", "-axo", "pid=,ppid=,rss="], 0.5, 1024 * 1024)


def test_unsupported_process_backend_is_explicit(monkeypatch):
    monkeypatch.setattr(resources.platform, "system", lambda: "Other")
    monkeypatch.setattr(resources, "_command", lambda *a: pytest.fail("Unexpected process read"))
    assert resources.read_process_rss(1)["reason"] == "unsupported_os"


def test_sampler_caps_data_filters_fields_and_separates_maxima(monkeypatch):
    monkeypatch.setattr(
        resources,
        "read_ollama_ps",
        lambda timeout: loaded(secret="test-only-never-retained", prompt="test-only-private-log"),
    )
    monkeypatch.setattr(resources, "read_process_rss", lambda timeout: rss())
    sampler = resources.ResourceSampler(MODEL, interval_seconds=5, max_samples=2)
    sampler.start()
    report = sampler.stop()
    assert report["status"] == "completed"
    assert report["sample_count"] == 2
    assert report["sample_limit_reached"] is True
    assert report["matching_model_sample_count"] == 2
    assert report["rss_complete_sample_count"] == 2
    assert report["sampled_maxima"] == {
        "ollama_reported_size_bytes": 1000,
        "ollama_reported_size_vram_bytes": 700,
        "listener_process_tree_rss_sum_bytes": 150 * 1024,
    }
    assert report["samples"][0]["ollama"]["models"][0]["digest"] == "test-only-digest"
    assert report["samples"][0]["ollama"]["models"][0]["context_length"] == 16384
    assert "test-only-never-retained" not in json.dumps(report)
    assert "test-only-private-log" not in json.dumps(report)
    assert report["external_process_isolation_guaranteed"] is False
    report["samples"].clear()
    assert len(sampler.stop()["samples"]) == 2


def test_missing_numeric_fields_are_unknown_and_foreign_names_not_collected(monkeypatch):
    value = loaded(size=True, size_vram=-1, context_length=None)
    value["models"].append({"model": "test-only-unrelated-private-name", "size": 99999})
    monkeypatch.setattr(resources, "read_ollama_ps", lambda timeout: value)
    monkeypatch.setattr(resources, "read_process_rss", lambda timeout: rss())
    sampler = resources.ResourceSampler(MODEL, max_samples=1)
    sampler.start()
    report = sampler.stop()
    assert report["foreign_model_observed"] is True
    assert report["samples"][0]["ollama"]["foreign_model_count"] == 1
    assert report["sampled_maxima"]["ollama_reported_size_bytes"] is None
    assert report["sampled_maxima"]["ollama_reported_size_vram_bytes"] is None
    assert "test-only-unrelated-private-name" not in json.dumps(report)


def test_read_errors_preserve_other_measurements_without_raw_error_text(monkeypatch):
    def failed(timeout):
        raise OSError("test-only-private-error-text")

    monkeypatch.setattr(resources, "read_ollama_ps", failed)
    monkeypatch.setattr(resources, "read_process_rss", lambda timeout: rss())
    sampler = resources.ResourceSampler(MODEL, max_samples=1)
    sampler.start()
    report = sampler.stop()
    assert report["status"] == "partial"
    assert report["error_count"] == 1
    assert report["ollama_sample_count"] == 0
    assert report["sampled_maxima"]["listener_process_tree_rss_sum_bytes"] == 150 * 1024
    assert report["samples"][0]["errors"] == [{"source": "ollama", "error_type": "OSError"}]
    assert "test-only-private-error-text" not in json.dumps(report)


def test_incomplete_process_tree_does_not_produce_complete_rss_maximum(monkeypatch):
    monkeypatch.setattr(resources, "read_ollama_ps", lambda timeout: loaded())
    monkeypatch.setattr(
        resources,
        "read_process_rss",
        lambda timeout: {**rss(), "tree_complete": False, "omitted_process_count": 1},
    )
    sampler = resources.ResourceSampler(MODEL, max_samples=1)
    sampler.start()
    report = sampler.stop()
    assert report["status"] == "partial"
    assert report["rss_incomplete_sample_count"] == 1
    assert report["sampled_maxima"]["listener_process_tree_rss_sum_bytes"] is None


def test_stop_waits_for_worker_and_no_reader_outlives_it(monkeypatch):
    entered, release = threading.Event(), threading.Event()
    main_thread = threading.get_ident()
    calls = []

    def reader(timeout):
        calls.append(threading.get_ident())
        if threading.get_ident() != main_thread and not release.is_set():
            entered.set()
            assert release.wait(2)
        return loaded()

    monkeypatch.setattr(resources, "read_ollama_ps", reader)
    monkeypatch.setattr(resources, "read_process_rss", lambda timeout: rss())
    sampler = resources.ResourceSampler(MODEL, interval_seconds=0.05, max_samples=3)
    sampler.start()
    assert entered.wait(2)
    result = []
    stopper = threading.Thread(target=lambda: result.append(sampler.stop()))
    stopper.start()
    assert sampler._stop.wait(2)
    assert not result
    release.set()
    stopper.join(2)
    assert not stopper.is_alive()
    assert not sampler._thread.is_alive()
    assert len(result[0]["samples"]) == len(calls) == 3


@pytest.mark.parametrize(
    "options",
    [
        {"max_samples": True},
        {"max_samples": 1001},
        {"interval_seconds": 0},
        {"timeout_seconds": float("nan")},
        {"timeout_seconds": 6},
    ],
)
def test_sampler_configuration_is_bounded(options):
    with pytest.raises(ValueError):
        resources.ResourceSampler(MODEL, **options)


@pytest.fixture
def session_environment(monkeypatch, tmp_path):
    events = []
    original_open, original_fdopen = cli.os.open, cli.os.fdopen

    def isolated_open(path, flags, mode=0o777, **kwargs):
        if str(path) == "/tmp/tracetrail-ollama.lock":
            path = tmp_path / "test-only-lock"
        return original_open(path, flags, mode, **kwargs)

    @contextmanager
    def tracked_fdopen(*args, **kwargs):
        with original_fdopen(*args, **kwargs) as stream:
            try:
                yield stream
            finally:
                events.append("lock_close")

    class Client:
        def __init__(self, **kwargs):
            assert kwargs["trust_env"] is False and kwargs["follow_redirects"] is False

        def ps(self):
            events.append("ps")
            return SimpleNamespace(models=[])

        def generate(self, **kwargs):
            events.append("unload")
            assert kwargs == {"model": cli.MODELS[0], "prompt": "", "keep_alive": 0}

    monkeypatch.setattr(cli.os, "open", isolated_open)
    monkeypatch.setattr(cli.os, "fdopen", tracked_fdopen)
    monkeypatch.setattr(cli.fcntl, "flock", lambda *args: events.append("lock"))
    monkeypatch.setattr(cli.ollama, "Client", Client)
    monkeypatch.setattr(cli, "verify_local_weights", lambda name: {"name": name})
    return events


def test_optional_sampler_stops_before_metadata_unload_and_lock_release(
    monkeypatch, session_environment
):
    events = session_environment

    class Sampler:
        def __init__(self, name):
            assert name == cli.MODELS[0]

        def start(self):
            events.append("sampler_start")

        def stop(self):
            events.append("sampler_stop")
            return {"status": "completed", "error_count": 0, "samples": []}

    monkeypatch.setattr(cli, "ResourceSampler", Sampler)
    with cli.model_session(cli.MODELS[0], measure_resources=True) as info:
        events.append("investigate")
    assert info["resources"]["status"] == "completed"
    assert events == [
        "lock",
        "ps",
        "sampler_start",
        "investigate",
        "sampler_stop",
        "ps",
        "unload",
        "lock_close",
    ]


def test_default_session_does_not_construct_sampler(monkeypatch, session_environment):
    monkeypatch.setattr(cli, "ResourceSampler", lambda name: pytest.fail("Unexpected sampler"))
    with cli.model_session(cli.MODELS[0]) as info:
        pass
    assert "resources" not in info


def test_sampler_stop_failure_preserves_session_result_and_unloads(
    monkeypatch, session_environment
):
    class Sampler:
        def __init__(self, name):
            pass

        def start(self):
            pass

        def stop(self):
            raise OSError("test-only-private-error")

    monkeypatch.setattr(cli, "ResourceSampler", Sampler)
    with cli.model_session(cli.MODELS[0], measure_resources=True) as info:
        info["test_only_raw_result"] = "preserved"
    assert info["test_only_raw_result"] == "preserved"
    assert info["resources"]["status"] == "unavailable"
    assert info["resources"]["errors"] == [{"phase": "stop", "error_type": "OSError"}]
    assert "test-only-private-error" not in json.dumps(info)
    assert session_environment[-2:] == ["unload", "lock_close"]


def test_sampler_start_failure_is_retained_after_stop(monkeypatch, session_environment):
    class Sampler:
        def __init__(self, name):
            pass

        def start(self):
            raise OSError("test-only-private-start-error")

        def stop(self):
            return {"status": "completed", "error_count": 0, "samples": []}

    monkeypatch.setattr(cli, "ResourceSampler", Sampler)
    with cli.model_session(cli.MODELS[0], measure_resources=True) as info:
        pass
    assert info["resources"]["status"] == "partial"
    assert info["resources"]["error_count"] == 1
    assert info["resources"]["errors"] == [{"phase": "start", "error_type": "OSError"}]
    assert "test-only-private-start-error" not in json.dumps(info)
    assert session_environment[-2:] == ["unload", "lock_close"]


def test_investigation_exception_still_stops_sampler_and_unloads(monkeypatch, session_environment):
    events = session_environment

    class Sampler:
        def __init__(self, name):
            pass

        def start(self):
            events.append("sampler_start")

        def stop(self):
            events.append("sampler_stop")
            return {"status": "completed", "error_count": 0, "samples": []}

    monkeypatch.setattr(cli, "ResourceSampler", Sampler)
    with pytest.raises(RuntimeError, match="Test-only investigation failure"):
        with cli.model_session(cli.MODELS[0], measure_resources=True):
            raise RuntimeError("Test-only investigation failure")
    assert events.index("sampler_stop") < events.index("unload") < events.index("lock_close")


@pytest.mark.parametrize("enabled", [False, True])
def test_run_case_passes_opt_in_only_when_enabled(monkeypatch, tmp_path, enabled):
    calls = []

    @contextmanager
    def session(name, **kwargs):
        calls.append((name, kwargs))
        yield {"name": name}

    monkeypatch.setattr(cli, "model_session", session)
    monkeypatch.setattr(cli.CloudTrailStore, "load", lambda path: object())
    monkeypatch.setattr(
        cli, "investigate", lambda *a, **kw: {"status": "completed", "failures": []}
    )
    monkeypatch.setattr(cli, "score_result", lambda *a: None)
    case = {
        "fixture": "test-only.json",
        "seed_event_id": "test-only",
        "question": "test-only",
        "hypotheses": [],
        "id": "test-only",
        "split": "development",
        "fixture_sha256": "test",
    }
    result = cli.run_case(case, tmp_path, cli.MODELS[0], "adaptive", measure_resources=enabled)
    assert result["status"] == "completed"
    assert calls == [(cli.MODELS[0], {"measure_resources": True} if enabled else {})]
