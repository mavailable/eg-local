import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { connectMQTT, Message } from "./mqtt";

// Composant pour afficher les voyants LED
function LEDIndicators({ ledStates, onLedToggle, deviceId }) {
  const ledColors = ['#ff4444', '#44ff44', '#4444ff', '#ffff44', '#ff44ff', '#44ffff'];
  
  return (
    <div style={{ margin: '20px 0' }}>
      <h3>LED Status</h3>
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        {ledStates.map((isOn, index) => (
          <div key={index} style={{ textAlign: 'center' }}>
            <div
              style={{
                width: '50px',
                height: '50px',
                borderRadius: '50%',
                backgroundColor: isOn ? ledColors[index] : '#333',
                border: `3px solid ${isOn ? '#fff' : '#666'}`,
                cursor: 'pointer',
                boxShadow: isOn ? `0 0 20px ${ledColors[index]}` : 'none',
                transition: 'all 0.3s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: isOn ? '#000' : '#666',
                fontWeight: 'bold'
              }}
              onClick={() => onLedToggle && onLedToggle(index)}
              title={`LED ${index + 1} - ${isOn ? 'ON' : 'OFF'} - Click to toggle`}
            >
              {index + 1}
            </div>
            <div style={{ fontSize: '12px', marginTop: '5px' }}>
              LED {index + 1}
            </div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: '10px', fontSize: '14px', color: '#666' }}>
        💡 Use keyboard keys 1-6 or GPIO buttons to toggle LEDs<br/>
        ⌨️ Web keyboard: Press keys 1-6 to control LEDs directly from this page
      </div>
    </div>
  );
}

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
  const [ledStates, setLedStates] = useState([false, false, false, false, false, false]);
  const [inputStatus, setInputStatus] = useState("disconnected");
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
      client.subscribe(`eg/dev/${deviceId}/input/leds`);
      client.subscribe(`eg/dev/${deviceId}/input/rfid`);
      client.subscribe(`eg/dev/${deviceId}/input/status`);

      client.onMessageArrived = (m) => {
        const topic = m.destinationName;
        let payload = {};
        try { payload = JSON.parse(m.payloadString); } catch {}
        
        if (topic === "eg/state/mode") {
          setMode(payload.mode);
        } else if (topic === `eg/dev/${deviceId}/res`) {
          if (payload.type === "wallet_get") setBalance(payload.balance_cents);
          if (payload.type === "wallet_debit" || payload.type === "wallet_credit") setBalance(payload.new_balance_cents);
        } else if (topic === "eg/night/step") {
          setStep(payload.step); 
          setQuestion(payload.question); 
          setOptions(payload.options || []);
        } else if (topic === `eg/dev/${deviceId}/input/leds`) {
          setLedStates(payload.states || [false, false, false, false, false, false]);
        } else if (topic === `eg/dev/${deviceId}/input/rfid`) {
          // Auto-remplir le tag UID depuis RFID
          setTagUid(payload.tag_uid || "");
        } else if (topic === `eg/dev/${deviceId}/input/status`) {
          setInputStatus(payload.status || "disconnected");
        }
      };
    })();
  }, []);

  // Gestion des touches clavier dans l'interface web
  useEffect(() => {
    const handleKeyPress = (event) => {
      const key = event.key;
      if (key >= '1' && key <= '6') {
        const ledIndex = parseInt(key) - 1;
        toggleLed(ledIndex);
        event.preventDefault();
      }
    };
    
    document.addEventListener('keydown', handleKeyPress);
    return () => {
      document.removeEventListener('keydown', handleKeyPress);
    };
  }, [ledStates]);

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
  
  // Fonctions pour contrôler les LEDs
  const toggleLed = (ledIndex) => {
    pub(`eg/dev/${deviceId}/input/cmd/led`, {
      index: ledIndex,
      state: !ledStates[ledIndex]
    });
  };
  
  const testLeds = () => {
    pub(`eg/dev/${deviceId}/input/cmd/test`, {
      action: "led_sequence"
    });
  };
  
  const simulateRfid = () => {
    const testTag = "04A37C91";
    pub(`eg/dev/${deviceId}/input/cmd/test`, {
      action: "simulate_rfid",
      tag_uid: testTag
    });
  };

  return (
    <div style={{ maxWidth: 640, margin: "20px auto", fontFamily: "system-ui, sans-serif" }}>
      <h2>Slot UI — {deviceId}</h2>
      <p><b>Mode:</b> {mode}</p>
      <p><b>MQTT:</b> {mqttHost}:{mqttPort}{mqttPath}</p>
      <p><b>Input Status:</b> <span style={{color: inputStatus === 'online' ? 'green' : 'red'}}>{inputStatus}</span></p>
      
      <div>
        <label>Tag UID: </label>
        <input 
          value={tagUid} 
          onChange={(e)=>setTagUid(e.target.value.trim().toUpperCase())} 
          placeholder="04A37C91" 
          style={{ marginRight: '10px', padding: '5px' }}
        />
        <button onClick={walletGet}>Balance</button>
        <button onClick={simulateRfid} style={{ marginLeft: '10px' }}>Simulate RFID</button>
      </div>
      <p><b>Balance:</b> {balance ?? "-"} cents</p>
      
      <div style={{ margin: '10px 0' }}>
        <button onClick={bet} style={{ marginRight: '10px' }}>Bet 200</button>
        <button onClick={credit}>Credit 500</button>
      </div>
      
      {/* Affichage des LEDs */}
      <LEDIndicators 
        ledStates={ledStates} 
        onLedToggle={toggleLed} 
        deviceId={deviceId}
      />
      
      <div style={{ margin: '10px 0' }}>
        <button onClick={testLeds}>Test LED Sequence</button>
      </div>
      
      {mode === "night" && (
        <div style={{ marginTop: 24, padding: 12, border: "1px solid #ddd", borderRadius: '8px' }}>
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
