from pydantic import BaseModel
from typing import List, Literal, Optional, Dict

class ModeIn(BaseModel):
    mode: Literal["day", "night"]

class NightStepIn(BaseModel):
    step: int
    question: str
    options: List[str]

class PayoutItem(BaseModel):
    payout_id: str
    source: Literal["roulette", "blackjack"]
    amount_cents: int
    meta: Optional[Dict] = None

class PayoutList(BaseModel):
    items: List[PayoutItem]
