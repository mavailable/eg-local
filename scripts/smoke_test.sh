#!/usr/bin/env bash
set -e

BROKER=localhost

echo "T1: UID inconnu -> balance 0, bet insuffisant"
mosquitto_pub -h $BROKER -t eg/core/wallet/get -m '{"req_id":"t1a","device_id":"slot-01","tag_uid":"04A37C91"}'
sleep 0.2
mosquitto_pub -h $BROKER -t eg/core/wallet/debit -m '{"req_id":"t1b","device_id":"slot-01","tag_uid":"04A37C91","amount_cents":200,"reason":"slot_bet"}'

echo "T2: credit 1000, bet 200, win 500"
mosquitto_pub -h $BROKER -t eg/core/wallet/credit -m '{"req_id":"t2a","device_id":"slot-01","tag_uid":"04A37C91","amount_cents":1000,"reason":"manual"}'
mosquitto_pub -h $BROKER -t eg/core/wallet/debit  -m '{"req_id":"t2b","device_id":"slot-01","tag_uid":"04A37C91","amount_cents":200,"reason":"slot_bet"}'
mosquitto_pub -h $BROKER -t eg/core/wallet/credit -m '{"req_id":"t2c","device_id":"slot-01","tag_uid":"04A37C91","amount_cents":500,"reason":"slot_win"}'

echo "T4: payout new 12500"
mosquitto_pub -h $BROKER -t eg/core/payouts/new -m '{"payout_id":"ulid_P123","source":"roulette","amount_cents":12500,"meta":{"round":"R123","seat":2}}'

echo "T7: mode night + step"
curl -s -X POST http://localhost:8000/api/mode -H 'content-type: application/json' -d '{"mode":"night"}' >/dev/null
curl -s -X POST http://localhost:8000/api/night/step -H 'content-type: application/json' -d '{"step":1,"question":"A/B/C ?","options":["A","B","C"]}' >/dev/null

echo "OK - smoke tests pushed messages. Open UIs to observe."
