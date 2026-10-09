# Changelog

All notable changes to the YouTube Live Translate project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased — P0 remediation review

- Stage and validate isolated runtime generations before activation; preserve
  working installs on dependency/model failures and roll back registration errors.
- Ignore inherited Python paths and test hostile module shadowing with real inference.
- Verify freshly installed packaged models in the canonical production gate;
  keep historical PoC benchmarks separate.
- Attempt real packaged extension/tab/Native Messaging acceptance with an actual
  extension ID. Current managed browser blocks loading; readiness remains pending.
- Correct installation, support and privacy claims to match current evidence.

The 1.0.0 entry below records original release claims, including user-readiness,
latency and layout claims. Those historical claims do not establish current
production acceptance. The published release is unchanged.

## [1.0.0] - 2026-09-02

### Added
- **V1 Product Release**: Transformed verified S0–S5 engineering demonstrator into an installable, user-ready Chrome extension and native runtime.
- **Chrome Native Messaging Integration**: Direct stdio communication between Chrome Extension and local CPU runtime without manual WebSocket port configuration.
- **Anchored Subtitle Presentation Layer**: Dual-box UI (solid committed box + dimmed provisional box) guaranteeing $0.0000\text{px}$ spatial anchor displacement.
- **Local Machine Translation**: Helsinki-NLP `opus-mt-ja-en` Marian INT8 CTranslate2 engine (~82 MB) running at sub-70ms latency.
- **Local Streaming ASR**: Sherpa-ONNX Japanese Zipformer Transducer INT8 running locally on CPU.
- **Incremental Translation State Machine**: Local Agreement ($K=2$) + Adaptive Frontier ($W=2$) policy with zero committed prefix revisions.
- **Deterministic Linux Runtime Package**: Standalone distribution package with automated `install.sh` and `uninstall.sh`.
- **Model Lifecycle Manager**: Automated SHA256 integrity verification, corruption detection, disk check, and model management.
- **Hardened YouTube Lifecycle**: Full SPA navigation handling, player recreation detection, fullscreen/theater mode adaptation, and ad transition awareness.
- **User Documentation**: Complete user guides for Installation, Quick Start, Troubleshooting, Privacy, and Support Matrix.
- **Chrome Web Store Specification**: Detailed permissions justifications and privacy disclosures in `CHROMEWEBSTORE.md`.

### Changed
- Converted extension identity from development PoC to production `"YouTube Live Translate"`.
- Redesigned popup UI into an intuitive control panel with YouTube tab detection and user settings.
- Standardized error codes and user-friendly error mappings across extension and native host.

### Historical Engineering Milestones
- **S5**: Anchored Subtitle Renderer & Native Host Integration (Passed).
- **S4**: Incremental Translation Policy & State Machine (Passed).
- **S3**: Local Machine Translation Engine Selection & INT8 Quantization (Passed).
- **S2**: Local Streaming ASR Feasibility & Performance Contract Gate (Frozen / Passed).
- **S1**: Tab Audio Capture & 16kHz PCM Downsampling via Offscreen Document (Passed).
- **S0**: Architecture Demonstrator & Evidence Ladder Foundation (Frozen).
