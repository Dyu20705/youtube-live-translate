# P0 remediation validation — 2026-10-09

Branch: `remediation/p0-runtime-extension`, based on `b8eb140`.
Scope: production content-script loading, model manifest/provisioning, isolated
runtime dependencies/installer, and exact Chrome extension ID registration.

Changes:

- The classic manifest content script dynamically imports modules using absolute
  extension URLs, with explicit initialization error reporting.
- A tracked model manifest pins the official ASR archive checksum, Marian source
  commit `0770961a39ba6bd66305b149c3f4110bcafca2e6`, source hashes and converted
  output hashes. Acquisition verifies source bytes before conversion and refuses
  to replace invalid existing assets. The ASR extractor reads the archive once
  and selects only required regular files. Runtime selects INT8 variants
  deterministically.
- Installation creates a production venv, installs pinned dependencies, acquires
  models, verifies checksums, runs CPU inference, and only then registers the
  host. The launcher never falls back to a developer or system interpreter.
- Missing or malformed IDs are rejected before filesystem changes. Registration
  contains one exact extension origin, preserves other installations, and records
  paths for safe uninstall. Release verification uses a disposable registry and
  runtime target instead of modifying the user's browser profile.

Verified in this cloud instance:

| Check | Result |
| --- | --- |
| Production acquisition/installer/registration/package suite | 13 passed |
| Classic production JS, real Chromium DOM/module loader with Chrome API harness | Passed |
| Package build and artifact digest/content checks | Passed |
| Official ASR acquisition and checksum checks | Passed |
| Canonical ASR recognition of Japanese speech fixture | Passed, nonempty Japanese text |
| Marian source verification, CPU INT8 conversion, model inference | Passed |
| Fresh runtime archive install with a new venv and isolated browser registry | Passed |
| Reinstallation with versioned output checksums, reusing verified models | Passed |
| Installed launcher: Japanese audio, intermediate/final subtitles, ping, stop, clean EOF | 1 passed |
| Fresh-install negative path without models | Failed as expected; no registration or SUCCESS |
| Actual packaged extension load / Chrome tab messaging | Blocked by administrator policy |

The successful installation used a synthetic, format-valid ID only in an
isolated test registry. It does not prove a real Chrome Native Messaging
connection. `test:extension` returned “Loading of unpacked extensions is disabled
by the administrator”; its result must remain blocked, distinct from the passing
Chrome API harness.

The installed-host test removed developer PYTHONPATH and executed the installed
launcher. It fed the tracked Japanese audio fixture, verified actual subtitle
messages and native protocol lifecycle, and got a nonempty English result.
Translation accuracy was not scored; the emitted fixture translation included
“The wind not sure if I'm going to be able to do that.” This result establishes
pipeline execution, not translation quality or product acceptance.

Reproduction commands are in `tests/README.md`. The first Marian attempt reached
Hugging Face metadata but failed at `us.aws.cdn.hf.co`; that required domain was
added to the environment draft. The standard HTTPS download path then completed,
with upstream hashes and TLS verification preserved.

Remaining acceptance: load the actual extension in a browser permitting
unpacked extensions, install with that browser's real ID, verify Native Messaging
and YouTube subtitles. The P1 reliability findings, long-session validation,
translation quality and complete historical PoC release suite remain separate
work. No release was published. These checks do not establish full release readiness.
