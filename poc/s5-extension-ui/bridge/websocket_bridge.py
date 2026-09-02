"""
websocket_bridge.py - WebSocket transport bridge for development and browser extension streaming.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Set
import websockets

try:
    from .runtime_pipeline import (
        StreamingTranslationRuntime,
        get_s2_asr_engine,
        get_s3_marian_engine
    )
    from .protocol import StatusMessage, ErrorMessage, serialize_wire_message
except (ImportError, ValueError):
    from runtime_pipeline import (
        StreamingTranslationRuntime,
        get_s2_asr_engine,
        get_s3_marian_engine
    )
    from protocol import StatusMessage, ErrorMessage, serialize_wire_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("websocket_bridge")

HOST = "127.0.0.1"
PORT = 8765

class WebSocketBridgeServer:
    def __init__(self, runtime: StreamingTranslationRuntime):
        self.runtime = runtime
        self.clients: Set[Any] = set()

    async def broadcast(self, message: str):
        if not self.clients:
            return
        disconnected = set()
        for client in self.clients:
            try:
                await client.send(message)
            except Exception:
                disconnected.add(client)
        self.clients -= disconnected

    async def handler(self, websocket):
        self.clients.add(websocket)
        logger.info(f"Client connected: {websocket.remote_address} (total clients: {len(self.clients)})")

        # Send initial READY status
        status = StatusMessage(state="RUNNING", message="S5 WebSocket Bridge Connected")
        await websocket.send(serialize_wire_message(status))

        try:
            async for message in websocket:
                if isinstance(message, bytes):
                    # Ingest PCM chunk
                    resp_json = self.runtime.process_pcm_chunk(message)
                    if resp_json:
                        await self.broadcast(resp_json)
                elif isinstance(message, str):
                    # Handle JSON control messages or synthetic text
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")
                        if msg_type == "control.start":
                            self.runtime.start()
                            await websocket.send(serialize_wire_message(StatusMessage(state="RUNNING", message="Capture started")))
                        elif msg_type == "control.stop":
                            self.runtime.stop()
                            await websocket.send(serialize_wire_message(StatusMessage(state="STOPPED", message="Capture stopped")))
                        elif msg_type == "synthetic.text":
                            # For benchmark / dev testing
                            src = data.get("text", "")
                            is_final = data.get("is_final", False)
                            resp_json = self.runtime.process_text_partial(src, is_final=is_final)
                            await self.broadcast(resp_json)
                    except Exception as e:
                        err = ErrorMessage(error_code="INVALID_CONTROL_MESSAGE", message=str(e))
                        await websocket.send(serialize_wire_message(err))

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {websocket.remote_address}")
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            self.clients.discard(websocket)

    async def start(self, host: str = HOST, port: int = PORT):
        logger.info(f"Starting S5 WebSocket Bridge on ws://{host}:{port}...")
        self.runtime.start()
        async with websockets.serve(self.handler, host, port):
            await asyncio.Future()  # run forever


def main():
    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    s2_model_dir = os.path.join(

        workspace_dir, "poc", "s2-streaming-asr", "models", "sherpa-onnx-streaming-zipformer-ar_en_id_ja_ru_th_vi_zh-2025-02-10"
    )
    s3_model_dir = os.path.join(
        workspace_dir, "poc", "s3-local-mt", "models", "opus-mt-ja-en-ct2-int8"
    )

    logger.info("Initializing S2 Zipformer and S3 Marian engines...")
    asr_engine = get_s2_asr_engine(s2_model_dir, num_threads=2)
    mt_engine = get_s3_marian_engine(s3_model_dir, num_threads=2)
    runtime = StreamingTranslationRuntime(asr_engine=asr_engine, mt_engine=mt_engine, k=2, buffer=2)

    server = WebSocketBridgeServer(runtime)
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")


if __name__ == "__main__":
    main()
