"""
error_codes.py - Standard error codes and user-friendly diagnostics for YouTube Live Translate.
"""

from typing import Dict

ERROR_MESSAGES: Dict[str, str] = {
    "MODEL_MISSING": "Translation model is not installed on your system. Please run the model downloader.",
    "MODEL_CORRUPT": "Translation model files are corrupt or incomplete. Please re-run verification.",
    "ENGINE_INIT_ERROR": "Failed to initialize local AI engines. Please check available memory and dependencies.",
    "AUDIO_DECODE_ERROR": "Received invalid or corrupt audio stream data from browser.",
    "OVERSIZED_MESSAGE": "Message exceeds allowable native messaging payload limit.",
    "MALFORMED_JSON": "Malformed JSON payload received over native messaging bridge.",
    "UNKNOWN_MESSAGE_TYPE": "Received unrecognized message type from extension.",
    "RUNTIME_ERROR": "An unexpected error occurred in the local translation runtime."
}


def get_user_friendly_error(code: str, fallback_detail: str = "") -> str:
    """Returns user-facing explanation for a technical error code."""
    msg = ERROR_MESSAGES.get(code, "A local runtime error occurred.")
    if fallback_detail and code not in ERROR_MESSAGES:
        return f"{msg} ({fallback_detail})"
    return msg
