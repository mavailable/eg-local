import os, threading
from fastapi import FastAPI
from typing import Dict
from .db import DB
from .mqtt_bus import MqttBus
from .schemas import ModeIn, NightStepIn, PayoutList

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
CORE_DEVICE_ID = os.getenv("CORE_DEVICE_ID", "core-01")
DB_PATH = os.getenv("DB_PATH", "/data/eg.db")
NIGHT_EXPECTED_VOTES = int(os.getenv("NIGHT_EXPECTED_VOTES", "9"))

app = FastAPI(title="EG Core", version="1.0.0")
db = DB(DB_PATH)
bus = MqttBus(client_id=CORE_DEVICE_ID, host=MQTT_HOST, port=MQTT_PORT)
current_step_lock = threading.Lock()
current_step = {"step": None}

def publish_mode(mode: str):
    bus.publish("eg/state/mode", {"mode": mode}, retain=True)

@app.on_event("startup")
def on_startup():
    bus.connect()
    bus.subscribe("eg/core/wallet/get", on_wallet_get)
    bus.subscribe("eg/core/wallet/debit", on_wallet_debit)
    bus.subscribe("eg/core/wallet/credit", on_wallet_credit)
    bus.subscribe("eg/core/payouts/new", on_payout_new)
    bus.subscribe("eg/core/payouts/claim", on_payout_claim)
    bus.subscribe("eg/night/vote", on_night_vote)
    mode = db.get_kv("mode") or "day"
    db.set_kv("mode", mode)
    publish_mode(mode)
    push_change_payouts()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/api/mode")
def set_mode(body: ModeIn):
    db.set_kv("mode", body.mode)
    publish_mode(body.mode)
    return {"ok": True, "mode": body.mode}

@app.post("/api/night/step")
def night_step(body: NightStepIn):
    with current_step_lock:
        current_step["step"] = body.step
    db.reset_votes_for_step(body.step)
    bus.publish("eg/night/step", {"step": body.step, "question": body.question, "options": body.options})
    return {"ok": True}

@app.get("/api/payouts", response_model=PayoutList)
def get_payouts():
    items = db.list_ready_payouts()
    return {"items": items}

def respond(device_id: str, payload: Dict):
    bus.publish(f"eg/dev/{device_id}/res", payload)

def on_wallet_get(topic: str, msg: dict):
    req_id = msg.get("req_id")
    device_id = msg.get("device_id", "unknown")
    tag_uid = msg.get("tag_uid")
    bal = db.get_balance(tag_uid) if tag_uid else 0
    respond(device_id, {"req_id": req_id, "type": "wallet_get", "status": "ok",
                        "balance_cents": bal})

def on_wallet_debit(topic: str, msg: dict):
    req_id = msg.get("req_id")
    device_id = msg.get("device_id", "unknown")
    tag_uid = msg.get("tag_uid")
    amount = int(msg.get("amount_cents", 0))
    reason = msg.get("reason", "debit")
    ok, new_bal = db.debit(device_id, tag_uid, amount, reason)
    status = "ok" if ok else "insufficient"
    respond(device_id, {"req_id": req_id, "type": "wallet_debit", "status": status,
                        "new_balance_cents": new_bal})

def on_wallet_credit(topic: str, msg: dict):
    req_id = msg.get("req_id")
    device_id = msg.get("device_id", "unknown")
    tag_uid = msg.get("tag_uid")
    amount = int(msg.get("amount_cents", 0))
    reason = msg.get("reason", "credit")
    new_bal = db.credit(device_id, tag_uid, amount, reason)
    respond(device_id, {"req_id": req_id, "type": "wallet_credit", "status": "ok",
                        "new_balance_cents": new_bal})

def on_payout_new(topic: str, msg: dict):
    payout_id = msg.get("payout_id")
    source = msg.get("source")
    amount = int(msg.get("amount_cents", 0))
    meta = msg.get("meta", {})
    if not payout_id:
        return
    db.insert_payout(payout_id, source, amount, meta)
    push_change_payouts()

def push_change_payouts():
    items = db.list_ready_payouts()
    bus.publish("eg/dev/change-01/payouts", {"items": items})

def on_payout_claim(topic: str, msg: dict):
    req_id = msg.get("req_id")
    device_id = msg.get("device_id", "change-01")
    payout_id = msg.get("payout_id")
    tag_uid = msg.get("tag_uid")
    status, credited_cents, new_balance = db.claim_payout(payout_id, device_id, tag_uid)
    respond(device_id, {
        "req_id": req_id, "type": "payout_claim", "status": status,
        "credited_cents": credited_cents, "new_balance_cents": new_balance
    })
    push_change_payouts()

def on_night_vote(topic: str, msg: dict):
    device_id = msg.get("device_id")
    step = int(msg.get("step", -1))
    choice = msg.get("choice")
    with current_step_lock:
        if step != current_step.get("step"):
            return
    if not device_id or not choice:
        return
    db.add_vote(step, device_id, choice)
    count = db.count_votes_for_step(step)
    if count >= NIGHT_EXPECTED_VOTES:
        bus.publish("eg/night/result", {"step": step, "status": "success", "next_step": step + 1})
