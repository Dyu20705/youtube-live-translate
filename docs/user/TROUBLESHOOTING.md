# Troubleshooting and recovery

If unpacked extension loading is disabled by an administrator, the real browser
test is blocked. Use an authorized environment that permits unpacked extensions;
do not substitute a mocked messaging harness for acceptance.

For an unreachable host, compare the actual ID in `chrome://extensions/` with
`allowed_origins` in `~/.config/google-chrome/NativeMessagingHosts/com.duy.youtube_live_translate.json`
(or the Chromium/custom config equivalent). The manifest must point to the
installed executable launcher. Reinstall using `./install.sh --extension-id YOUR_ACTUAL_EXTENSION_ID`.

Verify the installed runtime, not source-tree assets:

```bash
RUNTIME_DIR="$HOME/.local/share/youtube-live-translate"
"$RUNTIME_DIR/venv/bin/python" -I "$RUNTIME_DIR/models/model_manager.py" verify
"$RUNTIME_DIR/venv/bin/python" -I "$RUNTIME_DIR/models/model_manager.py" self-test
```

The native host uses length-prefixed JSON; piping raw JSON from `echo` is not a
valid test. See [production tests](../../tests/README.md) for real stdio framing
and separate Chrome Native Messaging acceptance.

A failed dependency install or model validation leaves the previous installation
active. Investigate the error and retry; never disable TLS or digest checks.
Corrupt active assets require investigation and reacquisition into a separate
target/profile before replacement. Retained generations consume disk space.

For capture failures, activate the YouTube tab and retry from the popup. For
missing subtitles, check Japanese audio, playback, and restart after navigation.
The popup’s Ready label does not prove the native host connected. Live-site,
quality and long-session behavior still require product validation.
