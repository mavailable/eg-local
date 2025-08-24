import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { connectMQTT, Message } from "./mqtt";

function App() {
  const params = new URLSearchParams(location.search);
  const deviceId = params.get("id") || "slot-01";
  
  // Configuration MQTT avec priorité : URL param > variable d'env > fallback
  const mqttHost = params.get("mqtt_host") || 
                   import.meta.env.VITE_MQTT_HOST || 
                   location.hostname;
  const mqttPort = parseInt(params.get("mqtt_port") || 
                           import.meta.env.VITE_MQTT_PORT || 
                           "9001");
  const mqttPath = params.get("mqtt_path") || 
                   import.meta.env.VITE_MQTT_PATH || 
                   "/mqtt";
  const [mode, setMode] = useState("day");
  const [balance, setBalance] = useState(null);
  const [step, setStep] = useState(null);
  const [question, setQuestion] = useState(null);
  const [options, setOptions] = useState([]);
  const [tagUid, setTagUid] = useState("");
  const clientRef = useRef(null);

  useEffect(() => {
    (async () => {
      const client = await connectMQTT({ 
        host: mqttHost, 
        port: mqttPort, 
        path: mqttPath, 
        clientId: deviceId + "-ui" 
      });
      clientRef.current = client;

      client.subscribe("eg/state/mode");
      client.subscribe(`eg/dev/${deviceId}/res`);
      client.subscribe("eg/night/step");

      client.onMessageArrived = (m) => {
        const topic = m.destinationName;
        let payload = {};
        try { payload = JSON.parse(m.payloadString); } catch {}
        if (topic === "eg/state/mode") setMode(payload.mode);
        else if (topic === `eg/dev/${deviceId}/res`) {
          if (payload.type === "wallet_get") setBalance(payload.balance_cents);
          if (payload.type === "wallet_debit" || payload.type === "wallet_credit") setBalance(payload.new_balance_cents);
        } else if (topic === "eg/night/step") {
          setStep(payload.step); setQuestion(payload.question); setOptions(payload.options || []);
        }
      };
    })();
  }, []);

  const pub = (topic, obj) => {
    const m = new Message(JSON.stringify(obj));
    m.destinationName = topic;
    m.qos = 1;
    clientRef.current?.send(m);
  };

  const walletGet = () => tagUid && pub("eg/core/wallet/get", { req_id: crypto.randomUUID(), device_id: deviceId, tag_uid: tagUid });
  const bet = () => tagUid && pub("eg/core/wallet/debit", { req_id: crypto.randomUUID(), device_id: deviceId, tag_uid: tagUid, amount_cents: 200, reason: "slot_bet" });
  const credit = () => tagUid && pub("eg/core/wallet/credit", { req_id: crypto.randomUUID(), device_id: deviceId, tag_uid: tagUid, amount_cents: 500, reason: "slot_win" });
  const vote = (choice) => pub("eg/night/vote", { device_id: deviceId, step: step || 1, choice, ts: Date.now().toString() });

  return (
    <div style={{ maxWidth: 520, margin: "20px auto", fontFamily: "system-ui, sans-serif" }}>
      <h2>Slot UI — {deviceId}</h2>
      <p><b>Mode:</b> {mode}</p>
      <p><b>MQTT:</b> {mqttHost}:{mqttPort}{mqttPath}</p>
      <div>
        <label>Tag UID: </label>
        <input value={tagUid} onChange={(e)=>setTagUid(e.target.value.trim().toUpperCase())} placeholder="04A37C91" />
        <button onClick={walletGet}>Balance</button>
      </div>
      <p><b>Balance:</b> {balance ?? "-"}</p>
      <div>
        <button onClick={bet}>Bet 200</button>
        <button onClick={credit}>Credit 500</button>
      </div>
      {mode === "night" && (
        <div style={{ marginTop: 24, padding: 12, border: "1px solid #ddd" }}>
          <h3>Vote — Step {step}</h3>
          <p>{question}</p>
          <div>
            {options?.map(o => <button key={o} onClick={()=>vote(o)} style={{ marginRight: 8 }}>{o}</button>)}
          </div>
        </div>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
