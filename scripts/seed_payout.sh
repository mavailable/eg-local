#!/usr/bin/env bash
BROKER=localhost
mosquitto_pub -h $BROKER -t eg/core/payouts/new -m '{"payout_id":"ulid_P'$(date +%s)'","source":"roulette","amount_cents":12500}'
