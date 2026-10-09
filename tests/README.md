# Production remediation checks

Run commands from the repository root. Keep test installations and browser
profiles separate from your real runtime and browser configuration.

```bash
bash scripts/build_release.sh
poc/s2-streaming-asr/.venv/bin/python -m pytest tests/test_production_setup.py -q
npm ci --prefix tests
npm run --prefix tests test:content
npm run --prefix tests test:extension
```

The Python suite requires pytest and checks source acquisition integrity,
corruption detection, exact native-host origins, registration preservation,
uninstall behavior, rejection of invalid installer arguments, and release
artifact checksums/content. It does not substitute fixture models for inference.

`test:content` runs the canonical classic content script in Chromium with mocked
Chrome messaging and actual browser module loading/DOM rendering. It verifies
that the previous static-import parsing failure is fixed, but does not prove
Chrome extension registration or Native Messaging.

`test:extension` loads the packaged extension into a disposable Chromium profile,
intercepts its YouTube page request locally, sends a wire subtitle through actual
Chrome tab messaging and checks rendering. It requires a browser/admin policy
that permits unpacked extensions. It exits with a failure if that capability is
blocked; do not describe that check as passing or substitute the harness result.
Chromium 151's Extensions CDP loading command is used; provide a compatible
binary through `CHROMIUM_BIN` when necessary. The default is `/usr/bin/chromium`.
No user-facing preview is started.

## Fresh install and inference

Extract the runtime tarball into a disposable directory and invoke its installer
with a real extension ID. Use `--target-dir` and `--browser-config-dir` to keep all
runtime and registration files inside a test sandbox. Do not change `HOME`.
The installed launcher must use the installed venv, verify both models, and
produce RUNNING, HEALTHY and STOPPED messages for a real stdio lifecycle. A final
check in Chrome with that ID is required to prove Native Messaging connects.

Offline negative check: install with `--skip-download` and no provisioned model
assets. Dependencies should install; the command must then return nonzero and
create no browser registration or SUCCESS message. This is a failure-path check,
not successful fresh-install validation.

Canonical models are acquired by `src/runtime/models/model_manager.py download`.
The versioned manifest pins the official ASR archive digest and the Marian source
commit/digests. Receipts lock every output digest after verified acquisition.
Use the installed venv for `model_manager.py verify` and `self-test`. Do not add
invented digests or disable TLS to unblock downloads.

The historical `scripts/verify_release.sh` still includes PoC paths/suites. Its installer now uses an isolated target and registry, but the PoC suites are
not the acceptance evidence for these production fixes; a complete release also
needs the remaining reliability and release-engineering work from the review.

Run installed speech/protocol checks with real model assets:

```bash
YLT_TEST_RUNTIME=/absolute/path/test-runtime \
  poc/s2-streaming-asr/.venv/bin/python -m pytest tests/test_installed_runtime.py -q -s
```

This starts the installed launcher with development PYTHONPATH removed, sends
Japanese fixture audio over the actual length-prefixed stdio protocol, checks
intermediate and final subtitles, then checks ping, stop, and clean EOF exit.
It does not establish a Chrome Native Messaging connection.
