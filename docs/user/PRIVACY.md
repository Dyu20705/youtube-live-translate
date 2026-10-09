# Local processing and data retention

The production Native Messaging path sends captured tab audio to a local runtime
through stdio. Sherpa-ONNX ASR and Marian/CTranslate2 translation run on CPU,
without a cloud translation API. Installation downloads Python dependencies and
model assets over HTTPS; YouTube itself requires network access. Historical
WebSocket development paths are separate from production acceptance.

There are no third-party analytics SDKs in the extension. Preferences use
`chrome.storage.local`. These statements describe the implementation, not an
independent privacy audit.

| Data | Location | Retention |
| --- | --- | --- |
| Captured audio | Runtime/browser memory | Processing buffers and browser recorded chunks may remain until the next capture or document teardown; immediate erasure is not guaranteed |
| Models and venv | Installed generation directories | Retained after unregistering and after upgrades; delete unwanted generations separately |
| Preferences | chrome.storage.local | Until cleared or extension removed |
| Diagnostics | stderr/terminal | Depends on whether the caller saves logs |

Avoid sharing diagnostic logs or audio fixtures containing private material.
