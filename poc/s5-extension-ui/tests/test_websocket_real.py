"""
test_websocket_real.py - Tier D: Real WebSocket transport and socket resilience tests.
Uses native asyncio.run with websockets.serve for robust socket testing.
"""

import asyncio
import pytest
import websockets
import json
import time
from pathlib import Path

from bridge.websocket_bridge import WebSocketBridgeServer
from bridge.runtime_pipeline import (
    StreamingTranslationRuntime,
    get_s2_asr_engine,
    get_s3_marian_engine
)
from bridge.protocol import parse_and_validate_wire_message

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent.parent
S2_MODEL_DIR = WORKSPACE_DIR / "poc" / "s2-streaming-asr" / "models" / "sherpa-onnx-streaming-zipformer-ar_en_id_ja_ru_th_vi_zh-2025-02-10"
S3_MODEL_DIR = WORKSPACE_DIR / "poc" / "s3-local-mt" / "models" / "opus-mt-ja-en-ct2-int8"


def test_websocket_real_connect_and_ping():
    async def _run():
        asr = get_s2_asr_engine(str(S2_MODEL_DIR), num_threads=2)
        mt = get_s3_marian_engine(str(S3_MODEL_DIR), num_threads=2)
        runtime = StreamingTranslationRuntime(asr_engine=asr, mt_engine=mt, k=2, buffer=2)
        runtime.start()

        bridge = WebSocketBridgeServer(runtime)
        port = 8771

        async with websockets.serve(bridge.handler, "127.0.0.1", port):
            async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
                init_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                init_msg = json.loads(init_raw)
                assert init_msg.get("type") == "status"
                assert init_msg.get("state") == "RUNNING"

                # Send synthetic PCM silence chunk
                silence_pcm = bytes(4096)
                await ws.send(silence_pcm)
                await asyncio.sleep(0.2)

    asyncio.run(_run())


def test_websocket_rapid_reconnect_resilience():
    async def _run():
        asr = get_s2_asr_engine(str(S2_MODEL_DIR), num_threads=2)
        mt = get_s3_marian_engine(str(S3_MODEL_DIR), num_threads=2)
        runtime = StreamingTranslationRuntime(asr_engine=asr, mt_engine=mt, k=2, buffer=2)
        runtime.start()

        bridge = WebSocketBridgeServer(runtime)
        port = 8772

        async with websockets.serve(bridge.handler, "127.0.0.1", port):
            for i in range(5):
                async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
                    init_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    init_msg = json.loads(init_raw)
                    assert init_msg.get("type") == "status"
                    assert init_msg.get("state") == "RUNNING"

    asyncio.run(_run())
