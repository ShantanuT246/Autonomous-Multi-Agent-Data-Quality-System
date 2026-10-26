import asyncio
import json
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class EventBroker:
    """Manages active Server-Sent Event (SSE) subscriber queues per run_id."""

    def __init__(self):
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, run_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(run_id, []).append(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue):
        if run_id in self._subscribers and queue in self._subscribers[run_id]:
            self._subscribers[run_id].remove(queue)
            if not self._subscribers[run_id]:
                del self._subscribers[run_id]

    async def broadcast_event(self, run_id: str, event_type: str, data: dict):
        if run_id in self._subscribers:
            payload = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
            for q in list(self._subscribers[run_id]):
                try:
                    await q.put(payload)
                except Exception as e:
                    logger.warning(f"Error publishing SSE event: {e}")


event_broker = EventBroker()
