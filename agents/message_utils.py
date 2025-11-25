from __future__ import annotations

from typing import Any, Iterable


def render_message(message: Any) -> str:
    """Normalize Strands agent messages (dict/list/objects) into plain text."""

    if message is None:
        return ""
    if isinstance(message, str):
        return message

    # Objects from Strands often expose ``content`` or ``message`` attributes
    if hasattr(message, "content"):
        return render_message(getattr(message, "content"))
    if hasattr(message, "message") and not isinstance(message, dict):
        return render_message(getattr(message, "message"))

    if isinstance(message, dict):
        if "text" in message:
            return str(message["text"])
        if "content" in message:
            return render_message(message["content"])
        if "message" in message:
            return render_message(message["message"])
        # Tool outputs may wrap text inside nested structures
        return "\n".join(
            part for part in (render_message(value) for value in message.values()) if part
        )

    if isinstance(message, Iterable):
        parts = [render_message(item) for item in message]
        return "\n".join(part for part in parts if part)

    return str(message)

