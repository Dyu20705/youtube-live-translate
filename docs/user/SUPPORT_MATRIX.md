# Support Matrix — Version 1.0.0

The following support matrix defines verified and supported platforms for **YouTube Live Translate 1.0.0**.

---

## Verified V1 Support

| Category | Supported / Verified | Status |
| :--- | :--- | :--- |
| **Operating System** | Linux x86_64 (glibc 2.31+) | **Supported (V1 Production)** |
| **Browser** | Google Chrome (version 116+), Chromium | **Supported (V1 Production)** |
| **Language Direction** | Japanese speech $\to$ English subtitles | **Supported (V1 Production)** |
| **Inference Hardware** | Multi-core x86_64 CPU | **Supported (V1 Production)** |
| **Platform Target** | YouTube Video (`/watch`) & YouTube Live (`/live`) | **Supported (V1 Production)** |
| **Cloud Dependencies** | None (100% Offline Local Inference) | **Zero Cloud Required** |

---

## Out of Scope for V1

The following platforms and capabilities are **NOT** part of the V1 release scope and will not be advertised until empirically verified in future releases:

- **Operating Systems:** Windows, macOS, Android, iOS.
- **Browsers:** Mozilla Firefox, Apple Safari, Microsoft Edge.
- **Languages:** English to Japanese, Chinese, Spanish, Korean, or arbitrary multilingual pairs.
- **Cloud Fallbacks:** Cloud LLMs, commercial translation APIs, remote GPUs.
