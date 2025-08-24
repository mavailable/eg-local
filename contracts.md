# Contrat de messagerie MQTT (extrait)

QoS: 1 pour finances/payouts/night — `eg/state/mode` **retained**.  
LWT agents: `eg/dev/<device_id>/status` = `online|offline`.

## Présence
- `eg/dev/<device_id>/hello` ← device `{ "type":"slot","version":"1.0.0","ts":"..." }`
- `eg/dev/<device_id>/status` (LWT): `online|offline`

## Mode & Night
- `eg/state/mode` (retained) → `{ "mode":"day"|"night" }`
- `eg/night/step` → `{ "step":1, "question":"...", "options":["A","B","C"] }`
- `eg/night/vote` ← slots → `{ "device_id":"slot-02", "step":1, "choice":"B", "ts":"..." }`
- `eg/night/result` → `{ "step":1, "status":"success", "next_step":2 }` (MVP)

## Wallet (RPC simple)
- Req: `eg/core/wallet/get` `{ "req_id","device_id","tag_uid" }`
- Res: `eg/dev/<device_id>/res` `{ "req_id","type":"wallet_get","status":"ok","balance_cents":12300 }`

- Req: `eg/core/wallet/debit` `{ "req_id","device_id","tag_uid","amount_cents":200,"reason":"slot_bet" }`
- Res: `eg/dev/<device_id>/res` `{ "req_id","type":"wallet_debit","status":"ok|insufficient","new_balance_cents":... }`

- Req: `eg/core/wallet/credit` `{ "req_id","device_id","tag_uid","amount_cents":500,"reason":"slot_win" }`
- Res: `eg/dev/<device_id>/res` `{ "req_id","type":"wallet_credit","status":"ok","new_balance_cents":... }`

## Payouts (tables → change)
- New: `eg/core/payouts/new` `{ "payout_id","source":"roulette","amount_cents":12500,"meta":{"round":"R123","seat":2} }`
- Liste: `eg/dev/change-01/payouts` `{ "items":[{"payout_id","source","amount_cents"}] }`
- Claim: `eg/core/payouts/claim` `{ "req_id","device_id":"change-01","payout_id","tag_uid" }`
- Res: `eg/dev/change-01/res` `{ "req_id","type":"payout_claim","status":"ok|not_found|already_claimed","credited_cents":...,"new_balance_cents":... }`
