"""Bounded, opt-in observations of local Ollama accounting and process RSS.

These are separate sampled measurements, not OS peak memory or an additive
CPU/GPU memory total. No prompt, process arguments, or environment is collected.
"""

from __future__ import annotations

import json
import math
import platform
import re
import subprocess
import sys
import threading
import time
from copy import deepcopy
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from tracetrail.local_model import OLLAMA_URL

_MAX_RESPONSE_BYTES = 64 * 1024
_MAX_PROCESSES = 64


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Resource metadata requests cannot redirect")


def _decode_models(data: bytes) -> dict:
    if len(data) > _MAX_RESPONSE_BYTES:
        raise ValueError("Resource metadata response exceeded its byte limit")
    value = json.loads(data)
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("models"), list)
        or len(value["models"]) > 64
        or any(not isinstance(item, dict) for item in value["models"])
    ):
        raise ValueError("Invalid loaded-model metadata")
    return value


def _read_ollama_ps(timeout: float) -> dict:
    """Read only the fixed loopback metadata endpoint, without ambient auth/proxies."""
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    request = Request(
        OLLAMA_URL + "/api/ps",
        headers={"Accept": "application/json", "Authorization": "local-only-no-auth"},
    )
    with opener.open(request, timeout=timeout) as response:
        data = response.read(_MAX_RESPONSE_BYTES + 1)
    return _decode_models(data)


def read_ollama_ps(timeout: float) -> dict:
    """Enforce a total deadline, including trickling headers/body, with a reader child.

    urllib's own timeout bounds inactivity, not total transfer time. The child
    only executes the fixed metadata reader; subprocess.run kills and waits for
    it on timeout, so no metadata worker outlives the model-session lock.
    """
    script = (
        "import json,sys; from tracetrail.resources import _read_ollama_ps; "
        "print(json.dumps(_read_ollama_ps(float(sys.argv[1])),ensure_ascii=False))"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", script, str(timeout)],
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError("Local resource metadata reader failed")
    return _decode_models(result.stdout)


def _command(args: list[str], timeout: float, max_bytes: int) -> str:
    result = subprocess.run(args, capture_output=True, check=False, timeout=timeout)
    # lsof exits 1 when no matching listener exists.
    if result.returncode not in (0, 1) or len(result.stdout) > max_bytes:
        raise ValueError("Process metadata was unavailable or exceeded its byte limit")
    return result.stdout.decode("ascii", errors="strict")


def process_tree_rss(listeners: str, processes: str) -> dict:
    """Parse numeric ps data; RSS on macOS is expressed in 1024-byte units."""
    roots = set()
    for value in listeners.splitlines():
        if not re.fullmatch(r"[0-9]{1,10}", value.strip()):
            raise ValueError("Invalid listener PID metadata")
        roots.add(int(value))
    rows = {}
    for line in processes.splitlines():
        parts = line.split()
        if len(parts) != 3 or any(not re.fullmatch(r"[0-9]{1,15}", p) for p in parts):
            raise ValueError("Invalid numeric process metadata")
        pid, parent, rss_kib = map(int, parts)
        if pid in rows:
            raise ValueError("Duplicate process PID metadata")
        rows[pid] = (parent, rss_kib)
    # Re-resolve the port listener every sample rather than retaining stale PIDs.
    selected = roots & rows.keys()
    while True:
        expanded = selected | {pid for pid, (parent, _) in rows.items() if parent in selected}
        if expanded == selected:
            break
        selected = expanded
    included = sorted(selected)[:_MAX_PROCESSES]
    entries = [
        {
            "pid": pid,
            "ppid": rows[pid][0],
            "role": "listener" if pid in roots else "descendant",
            "rss_bytes": rows[pid][1] * 1024,
        }
        for pid in included
    ]
    return {
        "source": "macos-ps-rss-kib",
        "listener_pids": sorted(roots),
        "processes": entries,
        "process_count": len(selected),
        "omitted_process_count": max(0, len(selected) - len(entries)),
        "rss_sum_bytes": sum(item["rss_bytes"] for item in entries) if entries else None,
        "tree_complete": bool(roots) and roots <= rows.keys() and len(selected) == len(entries),
    }


def read_process_rss(timeout: float) -> dict:
    if platform.system() != "Darwin":
        return {"source": "macos-ps-rss-kib", "available": False, "reason": "unsupported_os"}
    listeners = _command(
        ["/usr/sbin/lsof", "-nP", "-iTCP:11434", "-sTCP:LISTEN", "-t"], timeout, 4096
    )
    processes = _command(["/bin/ps", "-axo", "pid=,ppid=,rss="], timeout, 1024 * 1024)
    return {"available": True, **process_tree_rss(listeners, processes)}


def _integer(value):
    return value if type(value) is int and value >= 0 else None


def _text(value):
    return value if isinstance(value, str) and 0 < len(value) <= 256 else None


def _loaded_model_sample(raw: dict, name: str) -> dict:
    selected = []
    foreign = 0
    for item in raw["models"]:
        if item.get("model") != name and item.get("name") != name:
            foreign += 1
            continue
        selected.append(
            {
                "model": _text(item.get("model")),
                "name": _text(item.get("name")),
                "digest": _text(item.get("digest")),
                "size_bytes": _integer(item.get("size")),
                "size_vram_bytes": _integer(item.get("size_vram")),
                "context_length": _integer(item.get("context_length")),
            }
        )
    return {
        "loaded_model_count": len(raw["models"]),
        "matching_model_count": len(selected),
        "foreign_model_count": foreign,
        "models": selected[:8],
        "omitted_matching_model_count": max(0, len(selected) - 8),
    }


class ResourceSampler:
    """Sample one model session without loading, generating, or unloading a model."""

    def __init__(
        self,
        model_name: str,
        *,
        interval_seconds: float = 1.0,
        timeout_seconds: float = 1.0,
        max_samples: int = 900,
    ):
        for number in (interval_seconds, timeout_seconds):
            if (
                type(number) not in (int, float)
                or not math.isfinite(number)
                or not 0.05 <= number <= 5
            ):
                raise ValueError("Resource sampling interval/timeout must be between 0.05 and 5")
        if type(max_samples) is not int or not 1 <= max_samples <= 1000:
            raise ValueError("Resource sample limit must be between 1 and 1000")
        self.model_name = model_name
        self.interval = interval_seconds
        self.timeout = timeout_seconds
        self.limit = max_samples
        self.samples: list[dict] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._began: float | None = None
        self._report: dict | None = None

    def _collect(self, phase: str) -> None:
        if len(self.samples) >= self.limit:
            return
        began = time.monotonic()
        sample = {
            "index": len(self.samples),
            "elapsed_seconds": round(began - self._began, 6),
            "phase": phase,
            "errors": [],
        }
        for source, reader in (("ollama", read_ollama_ps), ("process_rss", read_process_rss)):
            try:
                value = reader(self.timeout)
                sample[source] = (
                    _loaded_model_sample(value, self.model_name) if source == "ollama" else value
                )
            except Exception as exc:
                sample["errors"].append({"source": source, "error_type": type(exc).__name__})
        sample["collection_seconds"] = round(time.monotonic() - began, 6)
        self.samples.append(sample)

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            if len(self.samples) >= self.limit:
                return
            self._collect("session")

    def start(self) -> None:
        if self._began is not None:
            raise RuntimeError("Resource sampler has already started")
        self._began = time.monotonic()
        self._collect("before_investigation")
        self._thread = threading.Thread(target=self._run, name="tracetrail-resources", daemon=False)
        try:
            self._thread.start()
        except Exception:
            self._thread = None
            raise

    def stop(self) -> dict:
        if self._began is None:
            raise RuntimeError("Resource sampler has not started")
        if self._report is not None:
            return deepcopy(self._report)
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
        self._collect("before_cleanup")

        def maximum(values):
            return max((value for value in values if value is not None), default=None)

        models = [model for s in self.samples for model in s.get("ollama", {}).get("models", [])]
        errors = sum(len(s["errors"]) for s in self.samples)
        rss_complete = sum(
            bool(s.get("process_rss", {}).get("tree_complete")) for s in self.samples
        )
        ollama_complete = sum("ollama" in s for s in self.samples)
        self._report = {
            "measurement": "local-resource-sampling-v1",
            "status": (
                "completed"
                if not errors and rss_complete == ollama_complete == len(self.samples)
                else "partial"
            ),
            "model": self.model_name,
            "requested_interval_seconds": self.interval,
            "read_timeout_seconds": self.timeout,
            "sample_limit": self.limit,
            "sample_count": len(self.samples),
            "sample_limit_reached": len(self.samples) >= self.limit,
            "duration_seconds": round(time.monotonic() - self._began, 6),
            "error_count": errors,
            "ollama_sample_count": ollama_complete,
            "matching_model_sample_count": sum(
                s.get("ollama", {}).get("matching_model_count", 0) > 0 for s in self.samples
            ),
            "rss_complete_sample_count": rss_complete,
            "rss_incomplete_sample_count": len(self.samples) - rss_complete,
            "foreign_model_observed": any(
                s.get("ollama", {}).get("foreign_model_count", 0) for s in self.samples
            ),
            "external_process_isolation_guaranteed": False,
            "sampled_maxima": {
                "ollama_reported_size_bytes": maximum(m["size_bytes"] for m in models),
                "ollama_reported_size_vram_bytes": maximum(m["size_vram_bytes"] for m in models),
                "listener_process_tree_rss_sum_bytes": maximum(
                    s.get("process_rss", {}).get("rss_sum_bytes")
                    for s in self.samples
                    if s.get("process_rss", {}).get("tree_complete")
                ),
            },
            "limitations": [
                "Periodic maxima can miss short peaks; API and process reads are sequential.",
                "Ollama-reported allocations and RSS overlap and must not be added.",
                "Process RSS sums can double-count shared mappings and are not model-only memory.",
                "Listener descendants are identified by sampled PID/PPID, not runner attribution.",
                "The TraceTrail lock does not control other applications using Ollama.",
            ],
            "samples": self.samples,
        }
        return deepcopy(self._report)
