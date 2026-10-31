#!/usr/bin/env python3
"""Check frozen inputs and server version without starting a study attempt.

This read-only check was added after the freeze. It sends only a loopback
metadata request. It does not reserve the server, load or unload weights,
check resource eligibility, or replace the frozen per-cell checks.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve()
sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location(
    "heldout_v9_server_check", SCRIPT.with_name("heldout_v9.py")
)
FROZEN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FROZEN)


def check(protocol):
    with FROZEN.no_network():
        frozen, _ = FROZEN.verify_protocol(protocol)
        expected = frozen["ollama_version"]
        FROZEN.require(
            expected == frozen["model"]["ollama_version"], "Frozen server version pins differ"
        )

    from tracetrail.local_model import local_json

    observed = local_json("/api/version").get("version")
    return {
        "check": "heldout-v9-server-version-v1",
        "scope": "frozen_inputs_and_server_version_only",
        "status": "passed" if observed == expected else "blocked",
        "expected_ollama_version": expected,
        "observed_ollama_version": observed,
        "checked_at": FROZEN.utc(),
        "protocol_sha256": FROZEN.sha(protocol),
        "checker_sha256": FROZEN.sha(SCRIPT),
        "inference_started": False,
        "server_reserved": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = check(args.protocol)
    except (ValueError, OSError, KeyError, AssertionError) as exc:
        print(f"Server check stopped: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return int(result["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
