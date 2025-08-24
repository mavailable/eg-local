import React, { useState } from "react";
import { createRoot } from "react-dom/client";

function App() {
  // Configuration API avec priorité : URL param > variable d'env > fallback
  const apiHost = new URLSearchParams(location.search).get("api_host") || 
                  import.meta.env.VITE_API_HOST || 
                  location.hostname;
  const apiPort = parseInt(new URLSearchParams(location.search).get("api_port") || 
                          import.meta.env.VITE_API_PORT || 
                          "8000");
  const base = `${location.protocol}//${apiHost}:${apiPort}`;
  const [mode, setMode] = useState("day");
  const [step, setStep] = useState(1);
  const [question, setQuestion] = useState("Choix ?");
  const [options, setOptions] = useState("A,B,C");
  const [log, setLog] = useState("");

  const post = async (path, body) => {
    const res = await fetch(base + path, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
    const j = await res.json();
    setLog((l)=> l + `\nPOST ${path} -> ${JSON.stringify(j)}`);
  };

  return (
    <div style={{ maxWidth: 540, margin: "20px auto", fontFamily: "system-ui, sans-serif" }}>
      <h2>Operator Panel</h2>
      <p><b>API:</b> {base}</p>
      <div style={{ border: "1px solid #ddd", padding: 12, marginBottom: 12 }}>
        <h3>Mode</h3>
        <select value={mode} onChange={(e)=>setMode(e.target.value)}>
          <option value="day">day</option>
          <option value="night">night</option>
        </select>
        <button onClick={()=>post("/api/mode", { mode })} style={{ marginLeft: 8 }}>Set Mode</button>
      </div>

      <div style={{ border: "1px solid #ddd", padding: 12 }}>
        <h3>Night Step</h3>
        <div>Step: <input type="number" value={step} onChange={(e)=>setStep(parseInt(e.target.value||"1"))} style={{ width: 80 }} /></div>
        <div>Question: <input value={question} onChange={(e)=>setQuestion(e.target.value)} style={{ width: 360 }} /></div>
        <div>Options (comma): <input value={options} onChange={(e)=>setOptions(e.target.value)} style={{ width: 320 }} /></div>
        <button onClick={()=>post("/api/night/step", { step, question, options: options.split(",").map(s=>s.trim()).filter(Boolean) })} style={{ marginTop: 8 }}>Send Step</button>
      </div>

      <pre style={{ marginTop: 16, whiteSpace: "pre-wrap" }}>{log}</pre>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
