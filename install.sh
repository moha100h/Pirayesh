#!/bin/bash
set -e

echo "========================================"
echo "   🪒  Pirayesh Bot — Installation"
echo "========================================"

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

echo ""
read -p "Bot Token (from @BotFather): " BOT_TOKEN
read -p "Admin Numeric ID (from @userinfobot): " ADMIN_IDS

# Create data directory for SQLite
mkdir -p data

cat > .env <<EOF
BOT_TOKEN=${BOT_TOKEN}
ADMIN_IDS=${ADMIN_IDS}
DATABASE_URL=sqlite+aiosqlite:////app/data/pirayesh.db
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
echo "✅ .env file created."
echo "🚀 Starting bot..."

docker compose up -d --build

echo ""
echo "========================================"
echo "✅ Pirayesh bot installed successfully!"
echo "Configure shop info from the bot admin panel."
echo "View logs: docker compose logs -f"
echo "========================================"
