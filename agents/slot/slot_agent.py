import asyncio, yaml, uuid, sys, os, logging
# Ensure parent dir (/agents) is on sys.path for 'common' import
CURRENT_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

from common.mqtt_async import AsyncMqtt
from common.input_manager import InputManager

def ulid_like():
    return uuid.uuid4().hex[:24]

class SlotAgent:
    def __init__(self, config_path: str):
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)
        self.device_id = cfg["device_id"]
        self.host = cfg["mqtt"]["host"]
        self.port = int(cfg["mqtt"]["port"])
        self.dev_mode = cfg.get("dev_mode", True)
        self.bet_amount = int(cfg.get("bet_amount_cents", 200))
        self.credit_amount = int(cfg.get("credit_amount_cents", 500))
        self.tag_uid = None
        self.mode = "day"
        self.bus = AsyncMqtt(client_id=self.device_id, host=self.host, port=self.port,
                             lwt_topic=f"eg/dev/{self.device_id}/status")
        
        # Gestionnaire d'entrées (GPIO, clavier, RFID)
        self.input_manager = InputManager(
            device_id=self.device_id,
            mqtt_host=self.host,
            mqtt_port=self.port,
            dev_mode=self.dev_mode
        )

    async def run(self):
        # Configuration des logs
        logging.basicConfig(level=logging.INFO)
        
        await self.bus.connect()
        self.bus.set_status_online(f"eg/dev/{self.device_id}/status")
        self.bus.publish(f"eg/dev/{self.device_id}/hello",
                         {"type":"slot","version":"1.0.0","ts": asyncio.get_event_loop().time()})
        self.bus.subscribe("eg/state/mode", self.on_mode)
        self.bus.subscribe(f"eg/dev/{self.device_id}/res", self.on_res)
        self.bus.subscribe("eg/night/step", self.on_night_step)
        
        # Souscription aux événements d'entrées
        self.bus.subscribe(f"eg/dev/{self.device_id}/input/rfid", self.on_rfid_tag)
        self.bus.subscribe(f"eg/dev/{self.device_id}/input/leds", self.on_led_update)
        
        print(f"[{self.device_id}] Connected. Dev mode: {self.dev_mode}.")
        print("Keyboard: r <UID> (scan), b (bet), c (credit), v <A|B|C> (vote), balance, q")
        print("Hardware: Use buttons 1-6 or keyboard keys 1-6 to toggle LEDs")
        
        # Démarrage du gestionnaire d'entrées en parallèle
        input_task = asyncio.create_task(self.input_manager.start())
        keyboard_task = asyncio.create_task(self.keyboard_loop())
        
        await asyncio.gather(input_task, keyboard_task)

    def on_mode(self, topic, msg):
        self.mode = msg.get("mode", "day")
        print(f"[{self.device_id}] Mode now: {self.mode}")

    def on_res(self, topic, msg):
        t = msg.get("type")
        if t == "wallet_get":
            print(f"[{self.device_id}] Balance: {msg.get('balance_cents')} cents")
        elif t in ("wallet_debit", "wallet_credit"):
            print(f"[{self.device_id}] {t} -> {msg.get('status')} | new_balance={msg.get('new_balance_cents')}")
        else:
            print(f"[{self.device_id}] Response: {msg}")

    def on_night_step(self, topic, msg):
        step = msg.get("step")
        q = msg.get("question")
        opts = msg.get("options")
        print(f"[{self.device_id}] NIGHT STEP {step}: {q} options={opts}")

    def on_rfid_tag(self, topic, msg):
        """Gestion des tags RFID détectés"""
        tag_uid = msg.get("tag_uid")
        if tag_uid:
            self.tag_uid = tag_uid
            print(f"[{self.device_id}] RFID TAG detected: {tag_uid}")
            # Lecture automatique du solde
            self.publish_wallet_get()
    
    def on_led_update(self, topic, msg):
        """Gestion des mises à jour d'état des LEDs"""
        states = msg.get("states", [])
        print(f"[{self.device_id}] LED states: {['ON' if s else 'OFF' for s in states]}")

    def publish_wallet_get(self):
        if not self.tag_uid:
            print("No tag. Use: r <UID>")
            return
        self.bus.publish("eg/core/wallet/get", {
            "req_id": ulid_like(),
            "device_id": self.device_id,
            "tag_uid": self.tag_uid
        })

    def publish_bet(self):
        if not self.tag_uid:
            print("No tag. Use: r <UID>")
            return
        self.bus.publish("eg/core/wallet/debit", {
            "req_id": ulid_like(),
            "device_id": self.device_id,
            "tag_uid": self.tag_uid,
            "amount_cents": self.bet_amount,
            "reason": "slot_bet"
        })

    def publish_credit(self):
        if not self.tag_uid:
            print("No tag. Use: r <UID>")
            return
        self.bus.publish("eg/core/wallet/credit", {
            "req_id": ulid_like(),
            "device_id": self.device_id,
            "tag_uid": self.tag_uid,
            "amount_cents": self.credit_amount,
            "reason": "slot_win"
        })

    def publish_vote(self, choice: str, step: int = None):
        self.bus.publish("eg/night/vote", {
            "device_id": self.device_id,
            "step": step or 1,
            "choice": choice,
            "ts": str(asyncio.get_event_loop().time())
        })

    async def keyboard_loop(self):
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        while True:
            line = (await reader.readline()).decode().strip()
            if not line:
                continue
            if line == "q":
                print("Bye.")
                break
            if line.startswith("r "):
                self.tag_uid = line.split(" ",1)[1].strip().upper()
                print(f"TAG set: {self.tag_uid}")
                self.publish_wallet_get()
            elif line == "b":
                self.publish_bet()
            elif line == "c":
                self.publish_credit()
            elif line.startswith("v "):
                choice = line.split(" ",1)[1].strip().upper()
                self.publish_vote(choice)
            elif line == "balance":
                self.publish_wallet_get()
            elif line.startswith("led "):
                # Nouvelle commande pour contrôler les LEDs
                try:
                    parts = line.split()[1:]
                    if len(parts) == 2:
                        led_index = int(parts[0])
                        state = parts[1].lower() in ('on', '1', 'true')
                        self.input_manager.set_led_state(led_index, state)
                    elif len(parts) == 1 and parts[0] == "test":
                        await self.input_manager.gpio_manager.test_sequence()
                except ValueError:
                    print("LED command format: led <0-5> <on|off> or led test")
            else:
                print("Commands: r <UID>, b, c, v <A|B|C>, balance, led <0-5> <on|off>, led test, q")

if __name__ == "__main__":
    cfg = sys.argv[1] if len(sys.argv) > 1 else "device_config.yaml"
    agent = SlotAgent(cfg)
    asyncio.run(agent.run())
