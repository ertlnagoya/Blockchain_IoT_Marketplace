from __future__ import annotations

import json
import logging
from threading import Event, Thread

import paho.mqtt.client as mqtt

from publisher.app.pipeline import MessageProcessor


logger = logging.getLogger(__name__)


class MQTTSubscriber:
    def __init__(
        self,
        host: str,
        port: int,
        topics: list[str],
        processor: MessageProcessor,
    ) -> None:
        self.host = host
        self.port = port
        self.topics = topics
        self.processor = processor
        self._stop = Event()
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._thread: Thread | None = None

        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def _on_connect(self, client: mqtt.Client, _userdata, _flags, reason_code, _properties):
        logger.info("mqtt connected reason=%s", reason_code)
        for topic in self.topics:
            client.subscribe(topic)
            logger.info("mqtt subscribed topic=%s", topic)

    def _on_message(self, _client: mqtt.Client, _userdata, msg: mqtt.MQTTMessage):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            self.processor.process_message(msg.topic, payload)
        except Exception:  # noqa: BLE001
            logger.exception("mqtt message processing failed topic=%s", msg.topic)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._client.connect(self.host, self.port, keepalive=60)
        self._thread = Thread(target=self._client.loop_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._client.disconnect()
        self._stop.set()
