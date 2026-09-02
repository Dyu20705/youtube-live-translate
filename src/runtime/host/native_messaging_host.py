#!/usr/bin/env python3
"""
native_messaging_host.py - Chrome Native Messaging host for YouTube Live Translate.
Reads/writes 32-bit native length-prefixed JSON via stdin/stdout.
Logs and diagnostics are written strictly to sys.stderr to prevent protocol contamination.
"""

import sys
import struct
import json
import os
import logging
from pathlib import Path

# Ensure all logging goes strictly to stderr
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="[NativeHost %(levelname)s] %(message)s")

MAX_MESSAGE_SIZE = 1024 * 1024  # 1 MiB Chrome Native Messaging limit

RUNTIME_ROOT = Path(__file__).resolve().parent.parent
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from host.protocol import StatusMessage, ErrorMessage, serialize_wire_message
from host.error_codes import get_user_friendly_error
from host.runtime_pipeline import StreamingTranslationRuntime
from engines.asr_engine import SherpaOnnxStreamingEngine
from engines.mt_engine import MarianCTranslate2Engine
from models.model_manager import ModelManager


def read_message() -> dict:
    """Reads a 32-bit native-endian length-prefixed message from stdin."""
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) == 0:
        return {}  # EOF
    if len(raw_length) < 4:
        logging.warning(f"Incomplete length prefix read: {len(raw_length)} bytes")
        return {"error": "MALFORMED_PREFIX"}

    message_length = struct.unpack("@I", raw_length)[0]
    if message_length > MAX_MESSAGE_SIZE:
        logging.error(f"Message exceeds 1 MiB limit: {message_length} bytes")
        return {"error": "OVERSIZED_MESSAGE", "size": message_length}

    message_bytes = sys.stdin.buffer.read(message_length)
    if len(message_bytes) < message_length:
        logging.error("Incomplete message body read")
        return {"error": "INCOMPLETE_BODY"}

    try:
        return json.loads(message_bytes.decode("utf-8"))
    except Exception as err:
        logging.error(f"Malformed JSON: {err}")
        return {"error": "MALFORMED_JSON", "details": str(err)}


def send_message(message: dict):
    """Sends a 32-bit native-endian length-prefixed JSON message to stdout."""
    encoded_content = json.dumps(message, ensure_ascii=False).encode("utf-8")
    encoded_length = struct.pack("@I", len(encoded_content))
    sys.stdout.buffer.write(encoded_length)
    sys.stdout.buffer.write(encoded_content)
    sys.stdout.buffer.flush()


def main():
    logging.info("Starting YouTube Live Translate Native Messaging Host...")

    # Check model presence & verification
    model_mgr = ModelManager()
    valid, errors = model_mgr.verify_all()
    if not valid:
        logging.error(f"Required models are missing or corrupted: {errors}")
        send_message(ErrorMessage(
            error_code="MODEL_MISSING",
            message=get_user_friendly_error("MODEL_MISSING")
        ).to_dict())
        sys.exit(1)

    try:
        asr_dir = model_mgr.get_model_path("asr")
        mt_dir = model_mgr.get_model_path("mt")

        asr_engine = SherpaOnnxStreamingEngine(str(asr_dir), language="ja", num_threads=2)
        asr_engine.initialize()

        mt_engine = MarianCTranslate2Engine(str(mt_dir), num_threads=2)
        mt_engine.initialize()

        runtime = StreamingTranslationRuntime(asr_engine=asr_engine, mt_engine=mt_engine, k=2, buffer=2)
        runtime.start()

        send_message(StatusMessage(state="RUNNING", message="Native Host Initialized").to_dict())
        logging.info("Native Host initialized successfully and emitted RUNNING state.")
    except Exception as e:
        logging.error(f"Failed to initialize engines: {e}")
        send_message(ErrorMessage(
            error_code="ENGINE_INIT_ERROR",
            message=get_user_friendly_error("ENGINE_INIT_ERROR", str(e))
        ).to_dict())
        sys.exit(1)

    # Main Stdio Loop
    while True:
        try:
            msg = read_message()
            if not msg:
                logging.info("Received EOF on stdin. Exiting native host cleanly.")
                break

            if "error" in msg:
                send_message(ErrorMessage(error_code=msg["error"], message=msg.get("details", "")).to_dict())
                continue

            msg_type = msg.get("type")
            if msg_type == "audio_chunk":
                raw_data = msg.get("data", "")
                try:
                    resp_json = runtime.process_encoded_audio(raw_data)
                    if resp_json:
                        send_message(json.loads(resp_json))
                except Exception as audio_err:
                    logging.warning(f"Audio processing error: {audio_err}")
                    send_message(ErrorMessage(
                        error_code="AUDIO_DECODE_ERROR",
                        message=get_user_friendly_error("AUDIO_DECODE_ERROR", str(audio_err))
                    ).to_dict())
            elif msg_type == "control.ping":
                send_message(StatusMessage(state="HEALTHY", message="pong").to_dict())
            elif msg_type == "control.stop":
                runtime.stop()
                send_message(StatusMessage(state="STOPPED", message="Translation stopped").to_dict())
            elif msg_type == "control.start":
                runtime.start()
                send_message(StatusMessage(state="RUNNING", message="Translation started").to_dict())
            elif msg_type == "control.flush":
                resp_json = runtime.finalize_stream()
                if resp_json:
                    send_message(json.loads(resp_json))
            else:
                logging.warning(f"Unknown message type: {msg_type}")
                send_message(ErrorMessage(
                    error_code="UNKNOWN_MESSAGE_TYPE",
                    message=f"Type {msg_type} unrecognized"
                ).to_dict())
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            send_message(ErrorMessage(
                error_code="RUNTIME_ERROR",
                message=get_user_friendly_error("RUNTIME_ERROR", str(e))
            ).to_dict())


if __name__ == "__main__":
    main()
