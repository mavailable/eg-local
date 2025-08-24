import json, threading
from typing import Callable, Dict
import paho.mqtt.client as mqtt

class MqttBus:
    def __init__(self, client_id: str, host: str, port: int):
        self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv5, transport="tcp")
        self.client.enable_logger()
        self.host, self.port = host, port
        self._handlers: Dict[str, Callable[[str, dict], None]] = {}
        self._connected = threading.Event()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def connect(self):
        self.client.connect(self.host, self.port, keepalive=30)
        self.client.loop_start()
        self._connected.wait(10)

    def _on_connect(self, client, userdata, flags, reason_code, props=None):
        self._connected.set()

    def subscribe(self, topic: str, handler: Callable[[str, dict], None]):
        self._handlers[topic] = handler
        self.client.subscribe(topic, qos=1)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8")) if msg.payload else {}
        except Exception:
            payload = {}
        handler = None
        if msg.topic in self._handlers:
            handler = self._handlers[msg.topic]
        else:
            for t, h in self._handlers.items():
                if self._match(t, msg.topic):
                    handler = h
                    break
        if handler:
            handler(msg.topic, payload)

    def _match(self, pattern: str, topic: str) -> bool:
        pp = pattern.split("/")
        tt = topic.split("/")
        for i, p in enumerate(pp):
            if p == "#":
                return True
            if i >= len(tt):
                return False
            if p == "+" or p == tt[i]:
                continue
            return False
        return len(pp) == len(tt)

    def publish(self, topic: str, obj: dict, retain: bool=False):
        self.client.publish(topic, payload=json.dumps(obj), qos=1, retain=retain)
