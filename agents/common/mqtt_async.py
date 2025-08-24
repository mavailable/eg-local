import json, asyncio
from typing import Callable, Dict
import paho.mqtt.client as mqtt

class AsyncMqtt:
    def __init__(self, client_id: str, host: str, port: int, lwt_topic: str):
        self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv5)
        self.client.will_set(lwt_topic, payload="offline", qos=1, retain=True)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.host, self.port = host, port
        self._handlers: Dict[str, Callable[[str, dict], None]] = {}
        self._connected = asyncio.Event()

    def _on_connect(self, client, userdata, flags, reason_code, props=None):
        self._connected.set()

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8")) if msg.payload else {}
        except Exception:
            payload = {}
        for pat, handler in self._handlers.items():
            if self._match(pat, msg.topic):
                handler(msg.topic, payload)

    def _match(self, pattern: str, topic: str) -> bool:
        pp = pattern.split("/")
        tt = topic.split("/")
        for i, p in enumerate(pp):
            if p == "#": return True
            if i >= len(tt): return False
            if p == "+" or p == tt[i]: continue
            return False
        return len(pp) == len(tt)

    async def connect(self):
        self.client.connect(self.host, self.port, keepalive=30)
        self.client.loop_start()
        await asyncio.wait_for(self._connected.wait(), timeout=10)

    def subscribe(self, topic: str, handler: Callable[[str, dict], None]):
        self._handlers[topic] = handler
        self.client.subscribe(topic, qos=1)

    def publish(self, topic: str, obj: dict, retain=False):
        self.client.publish(topic, json.dumps(obj), qos=1, retain=retain)

    def set_status_online(self, topic: str):
        self.client.publish(topic, "online", qos=1, retain=True)
