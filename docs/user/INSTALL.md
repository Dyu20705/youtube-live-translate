# Installation Guide — YouTube Live Translate

Supported target: Linux x86_64, Chrome/Chromium 116+, Python 3.12–3.13 with
`venv` support, Japanese speech → English subtitles on CPU. Development checks
currently run on Python 3.12. Allow several GB of disk space and RAM for acquisition/conversion; retained generations require additional disk. These are planning estimates, not verified minimums. Inference stays on your machine;
installation downloads Python packages and model assets.

## Load the extension and obtain its ID

1. Extract the extension ZIP. Select the directory containing `manifest.json`.
   For a source checkout, use `src/extension`.
2. Open `chrome://extensions/`, enable Developer mode, and choose **Load unpacked**.
3. Copy the actual extension ID shown there: exactly 32 lowercase letters a–p.
   Keep that directory in place; moving an unpacked extension can change its ID.

## Install the runtime

Extract the Linux runtime archive, then run from its extracted directory:

```bash
./install.sh --extension-id YOUR_ACTUAL_EXTENSION_ID
```

Replace `YOUR_ACTUAL_EXTENSION_ID` with the ID copied from Chrome. It is required;
the installer rejects missing IDs and placeholders before changing files.

The installer stages a new generation in a sibling `.TARGET_NAME.versions`
directory, creates its own venv, installs dependencies, verifies model digests,
and runs actual CPU ASR/MT inference before activating it. Existing assets are
copied and verified against the candidate manifest. Dependency or model failure
removes the candidate and preserves the active runtime and registrations.
The target becomes a stable symlink; its launcher resolves the generation and
ignores inherited `PYTHONPATH`/`PYTHONHOME`. Registration writes are atomic per
file and roll back on errors, together with the active symlink. Old generations
are retained for recovery. The first upgrade of an older direct-directory
installation briefly renames it before installing the symlink. Sudden process
termination/power loss during promotion is not covered by these rollback tests.
Do not interrupt promotion or manually edit active generation files.

The ASR archive comes from the official Sherpa-ONNX release and must match the
SHA256 in the tracked `models/model_manifest.json`. Marian is downloaded from
`Helsinki-NLP/opus-mt-ja-en`: acquisition uses the immutable commit and file digests recorded in the
tracked manifest, checks each source file against upstream LFS or Git blob
hashes, and converts it to CTranslate2 INT8 locally using CPU PyTorch. The versioned manifest also records expected converted output checksums. The model
receipt records the resolved revision, conversion version, and output digests.
Subsequent installs reuse verified assets. The receipt detects local corruption;
it is not a signed publisher attestation. The Marian source revision is pinned to
`0770961a39ba6bd66305b149c3f4110bcafca2e6`. Retain the receipt for provenance.

Model downloads require GitHub release asset access and Hugging Face access,
including its CDN/Xet destinations. If access is blocked, fix the network policy
and rerun the installer. Never disable TLS or integrity checks. Invalid copied assets cause candidate validation to fail. Preserve the active installation while investigating; use a separate target/profile for reacquisition rather than modifying active assets. PyTorch is needed
only for conversion; CTranslate2 handles runtime inference.

Custom installation and browser profile locations are supported:

```bash
./install.sh --extension-id YOUR_ACTUAL_EXTENSION_ID \
  --target-dir /absolute/path/runtime \
  --browser-config-dir /absolute/path/browser-config
```

`--browser-config-dir` replaces the normal `~/.config` base (or `XDG_CONFIG_HOME`),
containing `google-chrome/NativeMessagingHosts` and `chromium/NativeMessagingHosts`.
Use a separate target directory, outside the extracted runtime source. Existing
registrations for a different installation are preserved and cause an explicit
error. `--skip-download` verifies already provisioned assets and still performs
the self-test; it does not bypass model checks or dependency installation.

## Verify and use

For the default installation:

```bash
RUNTIME_DIR="$HOME/.local/share/youtube-live-translate"
"$RUNTIME_DIR/venv/bin/python" -I "$RUNTIME_DIR/models/model_manager.py" verify
"$RUNTIME_DIR/venv/bin/python" -I "$RUNTIME_DIR/models/model_manager.py" self-test
```

Reload the extension, open a Japanese YouTube video, and start translation.
Successful installation confirms local inference and registration; an actual
Chrome Native Messaging connection must still be verified in that browser
profile. If Chrome refuses the origin, compare the ID with the registered
`allowed_origins` and rerun installation with the correct ID.

## Uninstall

Run `uninstall.sh` from the installed runtime directory. It removes only the
registrations recorded by that installation, and only when they still point to
its launcher. Runtime files, the venv, and models are retained; remove that
stable target symlink and sibling `.TARGET_NAME.versions` directory separately if you no longer need any retained generation. An inactive generation refuses to unregister the active installation. Remove the
extension through `chrome://extensions/`.

Current browser acceptance is blocked by managed Chromium policy; see [review evidence](../evidence/remediation-p0/review-closure.md). Installation success alone does not establish release readiness.
