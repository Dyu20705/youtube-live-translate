# Remaining P0 review closure — 2026-10-09

Branch: `remediation/p0-runtime-extension`. This report supersedes the earlier
[validation snapshot](validation.md) for the remaining review findings. No merge,
tag, release upload or modification to the published 1.0.0 release was performed.

## Resolved findings

- `verify_release.sh` builds temporary candidates and invokes the extracted
  installer in a fresh target/profile. Model verification/self-test use the
  installed venv and installed model manager, never source-tree model weights.
  The source `src/runtime/models` contains only manager/manifest code, no weights.
- Reinstall stages dependencies and copied model assets in a separate generation.
  Real pip failure and corrupt candidate model validation preserve the previous
  runtime, manifest bytes and inference. Registration failure rolls back partially
  written profile manifests and activation, including after symlink upgrades.
  Successful promotion retains the prior generation and stable launcher path.
- The launcher resolves its physical generation, removes PYTHONPATH/PYTHONHOME,
  and uses isolated Python (`-I`). A poisoned-module regression exercises actual
  ASR/MT stdio inference without importing attacker-provided modules.
- Production acceptance is separate from historical PoC tests. Missing production
  prerequisites fail rather than skip. Documentation no longer claims user-ready
  acceptance from benchmarks, installation success or mocked Chrome APIs.

## Exact commands and outcomes

Run from `/workspace/youtube-live-translate`:

```bash
PIP_CACHE_DIR=/workspace/.cache/pip HF_HOME=/workspace/.cache/huggingface bash scripts/verify_release.sh
```

- Local candidate build: **PASS** (temporary outputs; no upload).
- Fresh packaged install: **PASS**, no source-tree model assets. Both pinned
  model verification and actual CPU Japanese → English inference self-test pass.
- Production suite: **20 passed in 332.07s**, **0 skipped** (13 production setup,
  2 installed speech/shadowing, 5 failure recovery/successful-upgrade tests).
- Actual packaged browser acceptance: **BLOCKED**, exit **2**. Consequently the
  entire gate returns **2**, not success. The earlier run before adding the
  symlink recovery case had 19 passed in 234.29s and the same browser block.

The final gate output was captured in `/workspace/ylt-production-acceptance-final.log`;
the earlier run is `/workspace/ylt-production-acceptance.log`. These local logs
are not portable repository artifacts; the exact commands and summary here,
and the committed browser report, are the review evidence.

The gate invokes these model checks on its freshly installed runtime (the
sandbox path is generated for each run):

```bash
"$YLT_TEST_RUNTIME/venv/bin/python" -I "$YLT_TEST_RUNTIME/models/model_manager.py" verify
"$YLT_TEST_RUNTIME/venv/bin/python" -I "$YLT_TEST_RUNTIME/models/model_manager.py" self-test
poc/s2-streaming-asr/.venv/bin/python -m pytest tests/test_production_setup.py tests/test_installed_runtime.py tests/test_upgrade.py -q
node tests/test_extension_loading.mjs
```

The isolated installer/stdio tests use a synthetic format-valid origin; they do
not establish Chrome acceptance. Fixture speech produces intermediate/final
subtitle events through actual installed CPU ASR/MT. Translation accuracy was
not scored. Existing download caches speed acquisition; source models and any
pre-existing runtime are not needed for the fresh target.

Independent browser reproduction:

```bash
YLT_BROWSER_REPORT=/workspace/ylt-browser-acceptance-final.json npm run --prefix tests test:extension
```

Exit **2, BLOCKED**, Chromium **151.0.7922.173**:

```text
cdpSession.send: Protocol error (Extensions.loadUnpacked): Loading of unpacked extensions is disabled by the administrator.
```

The machine-readable [browser report](browser-blocked.json) has
`extension_id: null`, `tab_messaging: false`, `native_messaging: false`.
The test attempted actual packaged loading in a disposable profile. No real
extension ID was obtained; neither real tab messaging nor Chrome Native Messaging
ran. No mock result substitutes for them. In an authorized environment allowing
unpacked extensions, the test obtains the actual ID, installs the packaged runtime
for that ID/profile, checks actual Chrome tab rendering and connects the real
native host with RUNNING/HEALTHY/STOPPED. That permitted-browser path remains
unverified here.

Additional local checks (all exit 0):

```bash
bash -n scripts/build_release.sh scripts/verify_release.sh src/runtime/install.sh src/runtime/uninstall.sh src/runtime/bin/youtube-live-translate-host
node --check tests/test_extension_loading.mjs
poc/s2-streaming-asr/.venv/bin/python -m compileall -q src/runtime/host tests/test_upgrade.py tests/test_installed_runtime.py
git diff --check
```

## Remaining risks and verdict

**CHANGES REQUIRED** before claiming full functional browser acceptance: rerun the
real packaged browser test in an authorized environment permitting unpacked
extensions. The browser block is environmental; no failed runtime inference is
being hidden by it. Real YouTube audio capture, translation quality and long
sessions remain pending product validation; historical benchmarks cannot close
those gaps.

Dependency/model/registration failures are covered, but abrupt SIGKILL or power
loss during promotion is not a tested crash-recovery guarantee. The first upgrade
from a legacy direct-directory installation has a brief rename/promotion window.
Retained generations consume disk and need manual cleanup after recovery is no
longer required. Python 3.13 and other Linux/hardware combinations remain untested.
Browser audio chunks are not guaranteed to be erased immediately; privacy docs
now describe the implementation’s actual retention.

## Changed files

Runtime/packaging: `scripts/build_release.sh`, `scripts/verify_release.sh`,
`src/runtime/install.sh`, `src/runtime/uninstall.sh`,
`src/runtime/bin/youtube-live-translate-host`,
`src/runtime/host/install_runtime.py`, `src/runtime/host/register_host.py`.

Tests: `tests/test_production_setup.py`, `tests/test_installed_runtime.py`,
`tests/test_upgrade.py`, `tests/test_extension_loading.mjs`, `tests/README.md`.

Documentation: `README.md`, `CHANGELOG.md`, `CHROMEWEBSTORE.md`,
`docs/user/INSTALL.md`, `docs/user/QUICKSTART.md`, `docs/user/SUPPORT_MATRIX.md`,
`docs/user/TROUBLESHOOTING.md`, `docs/user/PRIVACY.md`, this report and
`docs/evidence/remediation-p0/browser-blocked.json`.
