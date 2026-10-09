# Quick Start Guide

First follow [installation](INSTALL.md), using the actual loaded extension ID. The steps below describe the intended workflow; real YouTube end-to-end acceptance remains pending.

---

## 1. Open a Japanese YouTube Video or Live Stream
Navigate to any Japanese YouTube video or live broadcast (e.g. `https://www.youtube.com/watch?v=...` or `https://www.youtube.com/live/...`).

## 2. Open the Extension Popup
Click the **YouTube Live Translate** icon in the Chrome extension toolbar.
The popup detects supported YouTube URLs and may display **Ready**. This indicates page eligibility, not a verified native-host connection.

## 3. Start Live Translation
Click the blue **Start Live Translation** button in the popup.
Chrome will capture tab audio and send it to your local AI engine.

## 4. Watch Anchored English Subtitles
Subtitles will appear at the bottom of the video player:
- **Solid White Text:** Committed translation in the anchored layout; historical fixture geometry does not guarantee all page layouts.
- **Dimmed Italic Text:** Immediate provisional translation as new words are being spoken.

## 5. Stop Translation
When finished, open the popup and click **Stop Live Translation**, or simply close the YouTube tab.
