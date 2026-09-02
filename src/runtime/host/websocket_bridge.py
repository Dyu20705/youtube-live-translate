"""
websocket_bridge.py - Optional WebSocket bridge server for local development and diagnostics.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
import websockets

RUNTIME_ROOT = Path(__file__).resolve().parent.parent
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from host.protocol import StatusMessage, ErrorMessage, serialize_wire_message
from host.runtime_pipeline import StreamingTranslationRuntime
from engines.asr_engine import SherpaOnnxStreamingEngine
from engines.mt_engine import MarianCTranslate2Engine
from models.model_manager import ModelManager

logging.basicConfig(level=logging.INFO, format="[WS-Bridge %(levelname)s] %(message)s")


class WebSocketBridgeServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self.runtime: Optional[StreamingTranslationRuntime] = None

    def initialize(self):
        model_mgr = ModelManager()
        asr_dir = model_mgr.get_model_path("asr")
        mt_dir = model_mgr.get_model_path("mt")

        asr_engine = SherpaOnnxStreamingEngine(str(asr_dir), language="ja", num_threads=2)
        asr_engine.initialize()

        mt_engine = MarianCTranslate2Engine(str(mt_dir), num_threads=2)
        mt_engine.initialize()

        self.runtime = StreamingTranslationRuntime(asr_engine=asr_engine, mt_engine=mt_engine, k=2, buffer=2)
        self.runtime.start()

    async def handle_client(self, websocket):
        logging.info("Extension client connected over WebSocket.")
        await websocket.send(serialize_wire_message(StatusMessage(state="RUNNING", message="WebSocket bridge connected")))

        try:
            async for message in websocket:
                if isinstance(message, bytes):
                    resp_json = self.runtime.process_pcm_chunk(message)
                    if resp_json:
                        await websocket.send(resp_json)
                elif isinstance(message, str):
                    try:
                        data = json.loads(message)
                        m_type = data.get("type")
                        if m_type == "control.stop":
                            self.runtime.stop()
                            await websocket.send(serialize_wire_message(StatusMessage(state="STOPPED")))
                        elif m_type == "control.start":
                            self.runtime.start()
                            await websocket.send(serialize_wire_message(StatusMessage(state="RUNNING")))
                        elif m_type == "control.ping":
                            await websocket.send(serialize_wire_message(StatusMessage(state="HEALTHY", message="pong")))
                    except Exception:
                        pass
        except websockets.exceptions.ConnectionClosed:
            logging.info("Client disconnected.")

    async def run(self):
        self.initialize()
        logging.info(f"Serving WebSocket bridge on ws://{self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # run forever


def main():
    server = WebSocketBridgeServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
