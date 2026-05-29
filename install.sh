#!/bin/bash
set -e

echo "========================================"
echo "   🪒  نصب ربات پیرایش"
echo "========================================"

# بررسی Docker
if ! command -v docker &> /dev/null; then
    echo "📦 نصب Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    echo "📦 نصب Docker Compose..."
    apt-get install -y docker-compose-plugin 2>/dev/null || pip install docker-compose
fi

echo ""
echo "🔑 لطفاً اطلاعات زیر را وارد کنید:"
echo ""

read -p "توکن ربات (از @BotFather): " BOT_TOKEN
read -p "آیدی عددی ادمین: " ADMIN_IDS
read -p "نام آرایشگاه [پیرایش]: " SHOP_NAME
SHOP_NAME=${SHOP_NAME:-پیرایش}
read -p "شماره تلفن آرایشگاه: " SHOP_PHONE
read -p "آدرس آرایشگاه: " SHOP_ADDRESS
read -p "شماره کارت برای پرداخت: " CARD_NUMBER
read -p "نام صاحب کارت: " CARD_HOLDER

cat > .env <<EOF
BOT_TOKEN=${BOT_TOKEN}
ADMIN_IDS=${ADMIN_IDS}
BOOKING_ENABLED=true
PAYMENT_ENABLED=true
SERVICES_VISIBLE=true
CARD_NUMBER=${CARD_NUMBER}
CARD_HOLDER=${CARD_HOLDER}
SHOP_NAME=${SHOP_NAME}
SHOP_ADDRESS=${SHOP_ADDRESS}
SHOP_PHONE=${SHOP_PHONE}
DATABASE_URL=sqlite+aiosqlite:///pirayesh.db
EOF

echo ""
echo "✅ فایل .env ساخته شد."
echo "🚀 در حال راه‌اندازی ربات..."

docker compose up -d --build

echo ""
echo "========================================"
echo "✅ ربات پیرایش با موفقیت نصب شد!"
echo "برای مشاهده لاگ: docker compose logs -f"
echo "========================================"
