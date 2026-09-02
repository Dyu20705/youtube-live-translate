# Stage S1 Proof-of-Concept: YouTube Tab Audio Capture

**Stage Status:** `PASS` (Empirically Verified)  
**Objective:** Verify stable, low-latency, glitch-free audio capture from YouTube tabs under Chrome Manifest V3 using `tabCapture` + `Offscreen Document` downsampled to 16,000 Hz Mono 16-bit linear PCM.

---

## 1. Verified Capabilities

1. **Capture Stability:** Continuous tab audio capture from YouTube live streams and VODs without buffer underruns.
2. **Audio Passthrough:** Audio continues routing to system audio output (`source.connect(audioContext.destination)`) so the user can listen normally while capturing.
3. **Resampling Fidelity:** In-browser `AudioWorklet` downsamples native rates (48 kHz / 44.1 kHz) to 16,000 Hz mono linear PCM with phase continuity and zero per-call heap allocations.
4. **Export & Streaming:** Standalone export to 16 kHz RIFF `.wav` / raw `.pcm`, and real-time streaming to a local WebSocket receiver (`ws://localhost:8765`).

---

## 2. Installation & Quick Start

1. Open Google Chrome (or Chromium-based browser: Brave, Edge).
2. Navigate to `chrome://extensions/`.
3. Enable **Developer mode**.
4. Click **Load unpacked** and select:
   ```text
   poc/s1-audio-capture
   ```
5. The extension icon will appear in the browser toolbar.

---

## 3. Usage & Testing

### Mode A: Standalone In-Browser Recording
1. Open any YouTube live stream or video.
2. Click the extension icon in the toolbar.
3. Click **Start Capture**.
4. Observe the live VU signal meter and captured sample counters.
5. Click **Stop Capture**, then click **Download .WAV (16kHz)**.
6. Verify output properties using `ffprobe`:
   - Sample Rate: 16000 Hz
   - Channels: 1 (Mono)
   - Codec: pcm_s16le

### Mode B: Realtime Streaming to Local Host
1. Launch the standalone WebSocket receiver:
   ```bash
   pip install websockets
   python3 test_receiver.py
   ```
2. Open the extension popup, enable **Stream to Local Native Host** (`ws://localhost:8765`), and click **Start Capture**.
3. View real-time packet throughput, duration, and signal dBFS in the terminal.
