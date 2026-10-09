# Canonical production acceptance

Run from the repository root. Install test tooling with `npm ci --prefix tests`
and provide a Python environment containing pytest, numpy, scipy and soundfile.
The default test interpreter is `poc/s2-streaming-asr/.venv/bin/python`; this only
supplies test tooling and fixture resampling. Installed inference uses its own
venv and models, with no PoC engine imports.

```bash
PIP_CACHE_DIR=/workspace/.cache/pip HF_HOME=/workspace/.cache/huggingface bash scripts/verify_release.sh
```

The gate builds local candidates in a temporary distribution directory, extracts
the runtime archive, installs into an isolated target/profile and verifies
models with the installed interpreter/path. Source-tree model assets are not
required. It runs production setup, real installed speech/stdio lifecycle,
hostile PYTHONPATH shadowing, real dependency/model/registration failure recovery
and successful-upgrade tests. Missing prerequisites fail rather than skip.
The synthetic ID used for isolated stdio tests is not Chrome acceptance.

The final gate invokes the packaged extension loading test. It requires Chromium
with the Extensions CDP loading command (tested attempt on Chromium 151),
unpacked-extension permission and access to package/model download endpoints.
Set `CHROMIUM_BIN` for an authorized compatible browser. No HOME override is used.

```bash
YLT_BROWSER_REPORT=/absolute/path/browser-report.json npm run --prefix tests test:extension
```

This uses a disposable browser profile, the packaged extension and an intercepted
YouTube fixture page. It obtains the actual loaded extension ID, sends a real
Chrome tab message, installs the packaged runtime for that ID, then connects via
`chrome.runtime.connectNative` and checks RUNNING/HEALTHY/STOPPED. Policy blocks
return exit 2 and a BLOCKED report. No actual ID/Native Messaging success is claimed
when loading fails. This test does not establish live YouTube audio/quality.

For separate production suite execution, first build artifacts and prepare an
isolated installation with verified models:

```bash
YLT_TEST_RUNTIME=/absolute/path/test-runtime poc/s2-streaming-asr/.venv/bin/python -m pytest tests/test_production_setup.py tests/test_installed_runtime.py tests/test_upgrade.py -q
```

The speech test sends Japanese fixture audio over actual length-prefixed stdio,
checks subtitle events and clean stop/EOF. The shadow test deliberately supplies
poisonous Python modules through PYTHONPATH and verifies they are never loaded.
Upgrade tests perform real pip/validation/filesystem failures and check the old
installation still verifies, infers and completes its native lifecycle.

`npm run --prefix tests test:content` is a supplementary Chromium DOM harness with
mocked Chrome APIs, not extension or Native Messaging acceptance. Historical
`poc/` benchmarks remain separate; their saved results cannot satisfy this gate.
See [current results](../docs/evidence/remediation-p0/review-closure.md).
