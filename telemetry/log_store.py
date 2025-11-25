from __future__ import annotations

from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime
from threading import Lock
from typing import Any, Deque, Dict, List, Literal, Optional


Stage = Literal["input", "process", "tool", "output", "error"]


@dataclass
class LogEvent:
    timestamp: str
    agent: str
    stage: Stage
    message: str
    payload: Optional[Dict[str, Any]] = None

    def as_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


class AgentLogStore:
    def __init__(self, max_length: int = 2000) -> None:
        self._events: Deque[LogEvent] = deque(maxlen=max_length)
        self._lock = Lock()
        self._process_buffers: Dict[str, LogEvent] = {}

    def add(self, agent: str, stage: Stage, message: str, payload: Optional[Dict[str, Any]] = None) -> LogEvent:
        """Add a new event. Process-stage messages are consolidated per agent for readability."""

        normalized_message = message.strip() if isinstance(message, str) else str(message)
        event = LogEvent(
            timestamp=datetime.utcnow().isoformat(),
            agent=agent,
            stage=stage,
            message=normalized_message,
            payload=payload,
        )
        with self._lock:
            if stage == "process" and payload is None:
                existing = self._process_buffers.get(agent)
                if existing:
                    existing.message = f"{existing.message} {event.message}".strip()
                    existing.timestamp = event.timestamp
                    return existing
                self._events.append(event)
                self._process_buffers[agent] = event
                return event

            # Non-process events should clear any buffered process text for that agent
            self._process_buffers.pop(agent, None)
            self._events.append(event)
            return event

    def dump(self) -> List[LogEvent]:
        with self._lock:
            return list(self._events)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._process_buffers.clear()

    def as_dicts(self) -> List[Dict[str, Any]]:
        return [event.as_dict() for event in self.dump()]

    def tail(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock:
            events = list(self._events)[-limit:]
        return [event.as_dict() for event in events]
