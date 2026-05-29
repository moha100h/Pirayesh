import os
from dataclasses import dataclass, field

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: list = field(default_factory=lambda: [
        int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
    ])
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///pirayesh.db")

    BOOKING_ENABLED:  bool = os.getenv("BOOKING_ENABLED",  "true").lower() == "true"
    PAYMENT_ENABLED:  bool = os.getenv("PAYMENT_ENABLED",  "true").lower() == "true"
    SERVICES_VISIBLE: bool = os.getenv("SERVICES_VISIBLE", "true").lower() == "true"

    CARD_NUMBER:  str = os.getenv("CARD_NUMBER",  "")
    CARD_HOLDER:  str = os.getenv("CARD_HOLDER",  "")

    SHOP_NAME:    str = os.getenv("SHOP_NAME",    "پیرایش")
    SHOP_ADDRESS: str = os.getenv("SHOP_ADDRESS", "")
    SHOP_PHONE:   str = os.getenv("SHOP_PHONE",   "")

config = Config()
