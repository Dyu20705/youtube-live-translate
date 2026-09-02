#!/usr/bin/env bash
# uninstall.sh - Clean uninstallation of YouTube Live Translate Local Native Runtime

set -e

echo "Uninstalling YouTube Live Translate Local Runtime..."

CHROME_HOST_DIR="$HOME/.config/google-chrome/NativeMessagingHosts"
CHROMIUM_HOST_DIR="$HOME/.config/chromium/NativeMessagingHosts"

rm -f "$CHROME_HOST_DIR/com.duy.youtube_live_translate.json"
rm -f "$CHROMIUM_HOST_DIR/com.duy.youtube_live_translate.json"
echo "Removed browser Native Messaging Host manifests."

TARGET_DIR="${HOME}/.local/share/youtube-live-translate"
if [ -d "$TARGET_DIR" ]; then
    echo "Runtime installation directory: $TARGET_DIR"
    echo "To completely remove models and assets, run: rm -rf $TARGET_DIR"
fi

echo "Uninstallation complete."
