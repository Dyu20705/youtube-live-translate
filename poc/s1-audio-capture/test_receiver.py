#!/usr/bin/env python3
import asyncio
import sys
import time
import math
import struct

try:
    import websockets
except ImportError:
    print("Error: websockets package is required to run this test server.")
    print("Install via: pip install websockets")
    sys.exit(1)

HOST = "localhost"
PORT = 8765

class AudioStreamStats:
    def __init__(self):
        self.total_bytes = 0
        self.total_packets = 0
        self.start_time = None

    def update(self, chunk_len, dbfs):
        now = time.time()
        if self.start_time is None:
            self.start_time = now
        self.total_bytes += chunk_len
        self.total_packets += 1
        elapsed = now - self.start_time

        audio_duration_sec = self.total_bytes / (16000 * 2)
        bitrate_kbps = (self.total_bytes * 8 / 1000) / max(0.001, elapsed)

        print(f"\r[Stream] Pkts: {self.total_packets:4d} | "
              f"Audio: {audio_duration_sec:6.2f}s | "
              f"Data: {self.total_bytes/1024:7.1f} KB | "
              f"Bitrate: {bitrate_kbps:5.1f} kbps | "
              f"RMS: {dbfs:5.1f} dBFS", end="", flush=True)

def compute_rms_dbfs(pcm_bytes):
    count = len(pcm_bytes) // 2
    if count == 0:
        return -100.0
    samples = struct.unpack(f"<{count}h", pcm_bytes)
    sum_sq = sum(s * s for s in samples)
    rms = math.sqrt(sum_sq / count)
    if rms <= 0:
        return -100.0
    return 20 * math.log10(rms / 32768.0)

async def handler(websocket):
    print(f"\nClient connected: {websocket.remote_address}")
    stats = AudioStreamStats()
    try:
        async for message in websocket:
            if isinstance(message, bytes):
                dbfs = compute_rms_dbfs(message)
                stats.update(len(message), dbfs)
    except websockets.exceptions.ConnectionClosed:
        print("\nClient disconnected.")
    except Exception as e:
        print(f"\nError: {e}")

async def main():
    print(f"Listening on: ws://{HOST}:{PORT} (16kHz Mono 16-bit PCM)")
    async with websockets.serve(handler, HOST, PORT):
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nReceiver stopped.")
