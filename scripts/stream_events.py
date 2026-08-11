"""Shared parsing for line-delimited JSON emitted by host probe CLIs."""

from __future__ import annotations

import json
from collections.abc import Iterator


def iter_events(text: str) -> Iterator[dict[str, object]]:
    """Yield JSON object events, skipping diagnostics, malformed lines, and scalar values."""

    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            yield event


def iter_content_blocks(text: str) -> Iterator[dict[str, object]]:
    """Yield object blocks from mapping messages in transcript order."""

    for event in iter_events(text):
        message = event.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict):
                yield block
