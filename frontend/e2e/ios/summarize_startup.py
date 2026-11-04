# [Input] Explicit Simulator or iPhone console captures containing fixed DREAM_STARTUP metadata.
# [Output] Per-process phase measurements with the supplied target condition and incomplete-sample markers.
# [Pos] Offline APP-03 evidence reader; no app, account, network or model operations.
# [Sync] 2026-11-02: retain overlapping phase records and separate wall time from process CPU.

import argparse
import json
import math
from pathlib import Path


def read_measurements(text):
    records = []
    for number, line in enumerate(text.splitlines(), 1):
        if "DREAM_STARTUP " not in line:
            continue
        raw = line.split("DREAM_STARTUP ", 1)[1]
        try:
            value = json.loads(raw)
            if value["layer"] not in {"native", "cpython", "python"} or value["outcome"] not in {"ok", "failed"}:
                raise ValueError("unknown layer or outcome")
            if not isinstance(value["phase"], str) or not value["phase"]:
                raise ValueError("missing phase")
            for key in ("elapsedMs", "timestampMs", "pid"):
                if type(value[key]) not in {int, float} or not math.isfinite(value[key]) or value[key] < 0:
                    raise ValueError("invalid numeric metadata")
            if "processCpuMs" in value:
                cpu = value["processCpuMs"]
                if type(cpu) not in {int, float} or not math.isfinite(cpu) or cpu < 0:
                    raise ValueError("invalid CPU metadata")
            # Project only the measurement contract; unrelated console fields remain private.
            records.append({key: value[key] for key in (
                "layer", "phase", "outcome", "elapsedMs", "processCpuMs", "timestampMs", "pid", "attempt",
            ) if key in value})
        except (ValueError, KeyError, TypeError) as error:
            raise ValueError(f"Invalid DREAM_STARTUP metadata on line {number}") from error
    if not records:
        raise ValueError("No DREAM_STARTUP measurements found")
    return records


def summarize(records, condition):
    processes = []
    for pid in sorted({record["pid"] for record in records}):
        phases = sorted((record for record in records if record["pid"] == pid), key=lambda record: record["timestampMs"])
        processes.append({
            "pid": pid,
            "interpreterInitializationObserved": any(record["phase"] == "interpreter_initialize" for record in phases),
            "startupResults": [record for record in phases if record["phase"] == "startup_total"],
            "startupCompleted": any(record["phase"] == "startup_total" and record["outcome"] == "ok" for record in phases),
            "phases": phases,
        })
    return {"condition": condition, "durationsOverlap": True, "cpuScope": "application-process", "processes": processes}


def main():
    parser = argparse.ArgumentParser(description="Summarize APP-03 startup phase captures without launching an app.")
    parser.add_argument("console", type=Path)
    parser.add_argument("--condition", required=True, choices=("simulator", "iphone"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = summarize(read_measurements(args.console.read_text()), args.condition)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
