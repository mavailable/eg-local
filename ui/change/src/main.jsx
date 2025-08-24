import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { connectMQTT, Message } from "./mqtt";

function App() {
  const params = new URLSearchParams(location.search);
  const deviceId = params.get("id") || "change-01";
  const [payouts, setPayouts] = useState([]);
  const [tagUid, setTagUid] = useState("");
  const [lastRes, setLastRes] = useState(null);
  const clientRef = useRef(null);

  useEffect(() => {
    (async () => {
      const client = await connectMQTT({ host: location.hostname, port: 9001, path: "/mqtt", clientId: deviceId + "-ui" });
      clientRef.current = client;
      client.subscribe("eg/dev/change-01/payouts");
      client.subscribe(`eg/dev/${deviceId}/res`);
      client.onMessageArrived = (m) => {
        const topic = m.destinationName;
        let payload = {};
        try { payload = JSON.parse(m.payloadString); } catch {}
        if (topic === "eg/dev/change-01/payouts") setPayouts(payload.items || []);
        if (topic === `eg/dev/${deviceId}/res`) setLastRes(payload);
      };
    })();
  }, []);

  const pub = (topic, obj) => {
    const m = new Message(JSON.stringify(obj));
    m.destinationName = topic;
    m.qos = 1;
    clientRef.current?.send(m);
  };

  const claim = (payout_id) => {
    if (!tagUid) { alert("Tag UID requis"); return; }
    pub("eg/core/payouts/claim", {
      req_id: crypto.randomUUID(),
      device_id: deviceId,
      payout_id,
      tag_uid: tagUid.trim().toUpperCase()
    });
  };

  return (
    <div style={{ maxWidth: 640, margin: "20px auto", fontFamily: "system-ui, sans-serif" }}>
      <h2>Change Machine — {deviceId}</h2>
      <div style={{ marginBottom: 12 }}>
        <label>Tag UID:&nbsp;</label>
        <input value={tagUid} onChange={(e)=>setTagUid(e.target.value)} placeholder="04A37C91" />
      </div>
      <h3>Payouts prêts</h3>
      <ul>
        {payouts.map(p => (
          <li key={p.payout_id} style={{ marginBottom: 8 }}>
            <code>{p.payout_id}</code> — {p.source} — <b>{p.amount_cents}</b> cts &nbsp;
            <button onClick={() => claim(p.payout_id)}>Créditer</button>
          </li>
        ))}
      </ul>
      <div style={{ marginTop: 16, padding: 12, border: "1px solid #ddd" }}>
        <h4>Dernière réponse</h4>
        <pre>{JSON.stringify(lastRes, null, 2)}</pre>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
