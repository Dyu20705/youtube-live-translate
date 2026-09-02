#!/usr/bin/env python3
"""
run_e2e_verification.py - Master Verification Runner across All 6 Tiers for Stage S5.
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent.parent
PYTHON_EXE = WORKSPACE_DIR / "poc" / "s2-streaming-asr" / ".venv" / "bin" / "python"
PYTEST_EXE = WORKSPACE_DIR / "poc" / "s2-streaming-asr" / ".venv" / "bin" / "pytest"
EVIDENCE_DIR = WORKSPACE_DIR / "docs" / "evidence" / "s5-extension-ui"


def run_step(tier_name: str, cmd_list: list, pythonpath: str = None, cwd: Path = WORKSPACE_DIR) -> dict:
    print(f"\n[{tier_name}] Running: {' '.join(str(x) for x in cmd_list)}")
    env = os.environ.copy()
    if pythonpath:
        env["PYTHONPATH"] = f"{pythonpath}:{env.get('PYTHONPATH', '')}"
    else:
        env["PYTHONPATH"] = (
            f"{WORKSPACE_DIR}/poc/s5-extension-ui:"
            f"{WORKSPACE_DIR}/poc/s4-incremental-translation:"
            f"{WORKSPACE_DIR}/poc/s3-local-mt:"
            f"{WORKSPACE_DIR}/poc/s2-streaming-asr:"
            f"{env.get('PYTHONPATH', '')}"
        )

    t0 = time.perf_counter()
    res = subprocess.run(
        cmd_list,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    elapsed = time.perf_counter() - t0
    passed = (res.returncode == 0)
    status_str = "PASS" if passed else "FAIL"
    print(f"[{tier_name}] Result: {status_str} (Elapsed: {elapsed:.2f}s)")
    if not passed:
        print(f"--- FAILED OUTPUT ---\n{res.stdout}\n---------------------")
    return {
        "tier": tier_name,
        "command": " ".join(str(x) for x in cmd_list),
        "status": status_str,
        "passed": passed,
        "elapsed_sec": round(elapsed, 2),
        "output_tail": "\n".join(res.stdout.strip().splitlines()[-10:]) if res.stdout else ""
    }


def main():
    print("=" * 80)
    print("  STAGE S5 FULL 6-TIER E2E VERIFICATION SUITE")
    print("=" * 80)

    results = []

    s2_pp = f"{WORKSPACE_DIR}/poc/s2-streaming-asr"
    s3_pp = f"{WORKSPACE_DIR}/poc/s3-local-mt"
    s4_pp = f"{WORKSPACE_DIR}/poc/s4-incremental-translation:{WORKSPACE_DIR}/poc/s3-local-mt:{WORKSPACE_DIR}/poc/s2-streaming-asr"
    s5_pp = f"{WORKSPACE_DIR}/poc/s5-extension-ui:{WORKSPACE_DIR}/poc/s4-incremental-translation:{WORKSPACE_DIR}/poc/s3-local-mt:{WORKSPACE_DIR}/poc/s2-streaming-asr"

    # 1. Tier A — Automated Regression Suite
    results.append(run_step(
        "Tier A.1 — S2 Frozen Performance Contract Gate",
        [str(PYTHON_EXE), "poc/s2-streaming-asr/scripts/run_regression_check.py"],
        pythonpath=s2_pp
    ))
    results.append(run_step(
        "Tier A.2 — S3 Marian INT8 Regression Suite",
        [str(PYTEST_EXE), "poc/s3-local-mt/tests", "-q"],
        pythonpath=s3_pp
    ))
    results.append(run_step(
        "Tier A.3 — S4 Incremental MT Regression Suite",
        [str(PYTEST_EXE), "poc/s4-incremental-translation/tests", "-q"],
        pythonpath=s4_pp
    ))
    results.append(run_step(
        "Tier A.4 — S5 Python Unit & Pipeline Tests",
        [str(PYTEST_EXE), "poc/s5-extension-ui/tests/test_protocol.py", "poc/s5-extension-ui/tests/test_runtime_pipeline.py", "-q"],
        pythonpath=s5_pp
    ))
    results.append(run_step(
        "Tier A.5 — S5 Node.js Renderer Tests",
        ["node", "poc/s5-extension-ui/tests/test_renderer.mjs"]
    ))

    # 2. Tier B — Static & Packaging Contract
    results.append(run_step(
        "Tier B — Manifest V3 Packaging & Host Discovery Contract",
        [str(PYTEST_EXE), "poc/s5-extension-ui/tests/test_packaging_contract.py", "-v"],
        pythonpath=s5_pp
    ))

    # 3. Tier C — Real Native Messaging Stdio Suite (8 Scenarios)
    results.append(run_step(
        "Tier C — Real Native Messaging Stdio & 8 Failure Scenarios",
        [str(PYTEST_EXE), "poc/s5-extension-ui/tests/test_native_messaging_real.py", "-v"],
        pythonpath=s5_pp
    ))

    # 4. Tier D — Real WebSocket Transport Suite
    results.append(run_step(
        "Tier D — Real WebSocket Transport & Resiliency Suite",
        [str(PYTEST_EXE), "poc/s5-extension-ui/tests/test_websocket_real.py", "-v"],
        pythonpath=s5_pp
    ))

    # 5. Tier E — Browser Layout Geometry Invariant
    results.append(run_step(
        "Tier E — Multi-Resolution Browser Geometry & Anchor Invariant",
        ["node", "poc/s5-extension-ui/tests/test_browser_geometry.mjs"]
    ))

    # 6. Tier F — Fault Injection & Security Fuzzing
    results.append(run_step(
        "Tier F — Fault Injection & Security Fuzzing",
        [str(PYTEST_EXE), "poc/s5-extension-ui/tests/test_fault_injection.py", "-v"],
        pythonpath=s5_pp
    ))

    # 7. Tier G — Golden E2E Trace & Soak Testing
    results.append(run_step(
        "Tier G.1 — Golden E2E Audio Trace Replay",
        [str(PYTEST_EXE), "poc/s5-extension-ui/tests/test_golden_e2e.py", "-v"],
        pythonpath=s5_pp
    ))
    results.append(run_step(
        "Tier G.2 — Long-Running Soak & Memory Stability",
        [str(PYTEST_EXE), "poc/s5-extension-ui/tests/test_soak.py", "-v", "-s"],
        pythonpath=s5_pp
    ))

    # Summary
    all_passed = all(r["passed"] for r in results)
    total_time = sum(r["elapsed_sec"] for r in results)

    print("\n" + "=" * 80)
    print("  6-TIER E2E VERIFICATION MATRIX SUMMARY")
    print("=" * 80)
    print(f"{'Verification Step':<58} | {'Status':<8} | {'Time (s)':<8}")
    print("-" * 80)
    for r in results:
        print(f"{r['tier']:<58} | {r['status']:<8} | {r['elapsed_sec']:<8.2f}")
    print("=" * 80)

    verdict_unit = "PASS" if all(r["passed"] for r in results[:5]) else "FAIL"
    verdict_integration = "PASS" if all(r["passed"] for r in results[5:10]) else "FAIL"
    verdict_e2e = "PASS" if all(r["passed"] for r in results[10:]) else "FAIL"

    print(f"Overall S5 Unit / Contract:   {verdict_unit}")
    print(f"Overall S5 Integration:       {verdict_integration}")
    print(f"Overall S5 Real-world E2E:    {verdict_e2e}")
    print(f"Total Verification Time:      {total_time:.2f}s")
    print("=" * 80)

    report_payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "overall_status": "PASS" if all_passed else "FAIL",
        "verdicts": {
            "s5_unit_contract": verdict_unit,
            "s5_integration": verdict_integration,
            "s5_real_world_e2e": verdict_e2e
        },
        "total_elapsed_sec": round(total_time, 2),
        "steps": results
    }

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    report_file = EVIDENCE_DIR / "s5_e2e_verification_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2, ensure_ascii=False)
    print(f"\nEvidence artifact written to: {report_file}")

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
