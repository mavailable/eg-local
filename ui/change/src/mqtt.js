import { Client, Message } from "paho-mqtt";
export function connectMQTT({ host="localhost", port=9001, path="/mqtt", clientId }) {
  return new Promise((resolve, reject) => {
    const c = new Client(host, Number(port), path, clientId);
    c.onConnectionLost = () => console.warn("MQTT lost");
    c.connect({ timeout: 5, useSSL: false, onSuccess: () => resolve(c), onFailure: reject });
  });
}
export { Message };
