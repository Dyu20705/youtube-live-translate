# Installation Guide — YouTube Live Translate

Supported target: Linux x86_64, Chrome/Chromium 116+, Python 3.12–3.13 with
`venv` support, Japanese speech → English subtitles on CPU. Development checks
currently run on Python 3.12. Model acquisition and conversion need at least
3 GB free disk space and 4 GB available RAM. Inference stays on your machine;
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

The installer creates its own `venv`, installs pinned runtime dependencies,
provisions models, verifies their integrity, and runs an ASR/MT inference
self-test. Only then does it register the Native Messaging host for your exact
extension origin in Chrome and Chromium. It does not use the PoC environment or
models from a developer's home directory. Any failed step stops installation
without reporting success or creating a new host registration.

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
and rerun the installer. Never disable TLS or integrity checks. Invalid existing
assets are not overwritten: move them aside before reacquiring. PyTorch is needed
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
"$RUNTIME_DIR/venv/bin/python" "$RUNTIME_DIR/models/model_manager.py" verify
"$RUNTIME_DIR/venv/bin/python" "$RUNTIME_DIR/models/model_manager.py" self-test
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
installation directory separately if you no longer need them. Remove the
extension through `chrome://extensions/`.
