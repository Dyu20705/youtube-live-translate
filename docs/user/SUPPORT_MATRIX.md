# Target and verification matrix

The remediation branch retains the Japanese → English local CPU architecture.
The published 1.0.0 release has not been replaced. Targets are not blanket claims
of verified end-to-end support.

| Area | Target | Current evidence |
| --- | --- | --- |
| OS/runtime | Linux x86_64, Python 3.12–3.13 with venv | Fresh packaged install and inference tested on Linux/Python 3.12 |
| Browser | Chrome/Chromium 116+ with unpacked extensions allowed | Managed Chromium 151 blocks extension loading; actual tab/Native Messaging acceptance unverified |
| Languages | Japanese speech → English | Real installed ASR/MT fixture inference; quality not scored |
| Hardware | x86_64 CPU | CPU self-test; no broad hardware/minimum-resource certification |
| Site | YouTube watch/live pages | Real live audio and long sessions pending |
| Network | Local inference; downloads during installation | Verified HTTPS model acquisition; no cloud translation API required |

Windows, macOS, mobile, other browsers/languages and cloud fallback remain out of scope.
See [current evidence](../evidence/remediation-p0/review-closure.md).
