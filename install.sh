#!/bin/bash
set -e

echo "========================================"
echo "   🪒  نصب ربات پیرایش"
echo "========================================"

if ! command -v docker &> /dev/null; then
    echo "📦 نصب Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

echo ""
read -p "توکن ربات (از @BotFather): " BOT_TOKEN
read -p "آیدی عددی ادمین: " ADMIN_IDS

cat > .env <<EOF
BOT_TOKEN=${BOT_TOKEN}
ADMIN_IDS=${ADMIN_IDS}
DATABASE_URL=sqlite+aiosqlite:///pirayesh.db
BOOKING_ENABLED=true
PAYMENT_ENABLED=true
SERVICES_VISIBLE=true
CARD_NUMBER=
CARD_HOLDER=
SHOP_NAME=پیرایش
SHOP_ADDRESS=
SHOP_PHONE=
EOF

echo ""
echo "✅ فایل .env ساخته شد."
echo "🚀 در حال راه‌اندازی..."

docker compose up -d --build

echo ""
echo "========================================"
echo "✅ ربات با موفقیت نصب شد!"
echo "بقیه تنظیمات را از پنل مدیریت ربات انجام دهید."
echo "برای مشاهده لاگ: docker compose logs -f"
echo "========================================"
