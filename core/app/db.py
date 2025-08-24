import json, sqlite3, threading, time
from typing import Optional, Dict, Tuple, List

class DB:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._setup()

    def _setup(self):
        c = self._conn.cursor()
        c.execute("PRAGMA journal_mode=WAL;")
        c.execute("PRAGMA synchronous=NORMAL;")
        c.execute("""
        CREATE TABLE IF NOT EXISTS wallets(
            tag_uid TEXT PRIMARY KEY,
            balance_cents INTEGER NOT NULL DEFAULT 0,
            updated_at INTEGER NOT NULL
        );""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS payouts(
            payout_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            status TEXT NOT NULL,
            claimed_by_tag TEXT,
            meta TEXT,
            created_at INTEGER NOT NULL,
            claimed_at INTEGER
        );""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS tx_log(
            ts INTEGER NOT NULL,
            device_id TEXT,
            op TEXT,
            tag_uid TEXT,
            amount_cents INTEGER,
            details TEXT
        );""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS kv(
            k TEXT PRIMARY KEY,
            v TEXT NOT NULL
        );""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS night_votes(
            step INTEGER NOT NULL,
            device_id TEXT NOT NULL,
            choice TEXT NOT NULL,
            ts INTEGER NOT NULL
        );""")
        self._conn.commit()

    def now(self) -> int:
        return int(time.time())

    # KV
    def get_kv(self, k: str) -> Optional[str]:
        cur = self._conn.execute("SELECT v FROM kv WHERE k=?", (k,))
        row = cur.fetchone()
        return row["v"] if row else None

    def set_kv(self, k: str, v: str):
        with self._conn:
            self._conn.execute("INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))

    # Wallet helpers
    def ensure_wallet(self, tag_uid: str):
        ts = self.now()
        with self._conn:
            self._conn.execute(
                "INSERT INTO wallets(tag_uid, balance_cents, updated_at) VALUES(?,?,?) "
                "ON CONFLICT(tag_uid) DO NOTHING",
                (tag_uid, 0, ts)
            )

    def get_balance(self, tag_uid: str) -> int:
        self.ensure_wallet(tag_uid)
        cur = self._conn.execute("SELECT balance_cents FROM wallets WHERE tag_uid=?", (tag_uid,))
        row = cur.fetchone()
        return row["balance_cents"] if row else 0

    def credit(self, device_id: str, tag_uid: str, amount_cents: int, reason: str) -> int:
        ts = self.now()
        with self._lock:
            with self._conn:
                self.ensure_wallet(tag_uid)
                self._conn.execute(
                    "UPDATE wallets SET balance_cents = balance_cents + ?, updated_at=? WHERE tag_uid=?",
                    (amount_cents, ts, tag_uid)
                )
                new_balance = self.get_balance(tag_uid)
                self._conn.execute("INSERT INTO tx_log(ts, device_id, op, tag_uid, amount_cents, details) VALUES(?,?,?,?,?,?)",
                                   (ts, device_id, "credit", tag_uid, amount_cents, reason))
                return new_balance

    def debit(self, device_id: str, tag_uid: str, amount_cents: int, reason: str) -> Tuple[bool, int]:
        ts = self.now()
        with self._lock:
            with self._conn:
                self.ensure_wallet(tag_uid)
                cur = self._conn.execute(
                    "UPDATE wallets SET balance_cents = balance_cents - ?, updated_at=? "
                    "WHERE tag_uid=? AND balance_cents >= ?",
                    (amount_cents, ts, tag_uid, amount_cents)
                )
                if cur.rowcount == 0:
                    bal = self.get_balance(tag_uid)
                    self._conn.execute("INSERT INTO tx_log(ts, device_id, op, tag_uid, amount_cents, details) VALUES(?,?,?,?,?,?)",
                                       (ts, device_id, "debit_insufficient", tag_uid, amount_cents, reason))
                    return False, bal
                new_balance = self.get_balance(tag_uid)
                self._conn.execute("INSERT INTO tx_log(ts, device_id, op, tag_uid, amount_cents, details) VALUES(?,?,?,?,?,?)",
                                   (ts, device_id, "debit", tag_uid, amount_cents, reason))
                return True, new_balance

    # Payouts
    def insert_payout(self, payout_id: str, source: str, amount_cents: int, meta: Dict):
        ts = self.now()
        meta_json = json.dumps(meta or {})
        with self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO payouts(payout_id, source, amount_cents, status, meta, created_at) "
                "VALUES(?,?,?,?,?,?)",
                (payout_id, source, amount_cents, "ready", meta_json, ts)
            )

    def list_ready_payouts(self) -> List[Dict]:
        cur = self._conn.execute("SELECT payout_id, source, amount_cents FROM payouts WHERE status='ready' ORDER BY created_at ASC")
        return [dict(r) for r in cur.fetchall()]

    def claim_payout(self, payout_id: str, device_id: str, tag_uid: str):
        ts = self.now()
        with self._lock:
            with self._conn:
                cur = self._conn.execute("SELECT payout_id, amount_cents, status FROM payouts WHERE payout_id=?", (payout_id,))
                row = cur.fetchone()
                if not row:
                    return "not_found", None, None
                if row["status"] != "ready":
                    return "already_claimed", None, None
                amount = int(row["amount_cents"])
                self._conn.execute("UPDATE payouts SET status='claimed', claimed_by_tag=?, claimed_at=? WHERE payout_id=?",
                                   (tag_uid, ts, payout_id))
                new_balance = self.credit(device_id, tag_uid, amount, f"payout_claim:{payout_id}")
                self._conn.execute("INSERT INTO tx_log(ts, device_id, op, tag_uid, amount_cents, details) VALUES(?,?,?,?,?,?)",
                                   (ts, device_id, "payout_claim", tag_uid, amount, payout_id))
                return "ok", amount, new_balance

    # Night votes (log)
    def reset_votes_for_step(self, step: int):
        with self._conn:
            self._conn.execute("DELETE FROM night_votes WHERE step=?", (step,))

    def add_vote(self, step: int, device_id: str, choice: str):
        ts = self.now()
        with self._conn:
            self._conn.execute("INSERT INTO night_votes(step, device_id, choice, ts) VALUES(?,?,?,?)",
                               (step, device_id, choice, ts))

    def count_votes_for_step(self, step: int) -> int:
        cur = self._conn.execute("SELECT COUNT(*) AS c FROM night_votes WHERE step=?", (step,))
        return int(cur.fetchone()["c"])
