import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN        = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS        = list(map(int, os.getenv("ADMIN_IDS", "0").split(",")))
    DATABASE_URL     = os.getenv("DATABASE_URL", "sqlite+aiosqlite:////app/data/pirayesh.db")
    BOOKING_ENABLED  = os.getenv("BOOKING_ENABLED",  "true").lower() == "true"
    PAYMENT_ENABLED  = os.getenv("PAYMENT_ENABLED",  "true").lower() == "true"
    SERVICES_VISIBLE = os.getenv("SERVICES_VISIBLE", "true").lower() == "true"
    CARD_NUMBER      = os.getenv("CARD_NUMBER", "")
    CARD_HOLDER      = os.getenv("CARD_HOLDER", "")
    SHOP_NAME        = os.getenv("SHOP_NAME",    "پیرایش")
    SHOP_ADDRESS     = os.getenv("SHOP_ADDRESS", "")
    SHOP_PHONE       = os.getenv("SHOP_PHONE",   "")

config = Config()
