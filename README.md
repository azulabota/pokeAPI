# PokeAPI — Pokémon Card Stock Tracker

Check **Target** and **Best Buy** for Pokémon card restocks and get Telegram alerts.

**Free to run.** No paid APIs needed.

## How It Works

- **Target** — Uses Playwright (headless Chromium) to load product pages and intercept the internal API that returns store-level stock. Same data the website shows, no proxy service needed.
- **Best Buy** — Uses their free public developer API. Quick HTTPS calls, no browser needed.
- **SQLite DB** — Logs every check so you can see restock patterns over time.
- **Telegram alerts** — Instant notification when stock flips from out → in.

## Setup

### 1. Get API Keys (free)

- **Best Buy:** [developer.bestbuy.com](https://developer.bestbuy.com) → "Get Started" → free key
- **Telegram bot:**
  1. Message [@BotFather](https://t.me/BotFather) → `/newbot` → pick a name → get token
  2. Message [@userinfobot](https://t.me/userinfobot) → `/start` → get your chat ID
  3. Start your bot: open `t.me/<your_bot_username>` and click Start

### 2. Configure

```bash
cp .env.example .env
# Edit .env — add your API keys, ZIP codes
```

### 3. Install & Run

```bash
pip install -r requirements.txt
python3 -m playwright install chromium
python run.py
```

### 4. Schedule (auto-check)

**Cron** (every 30 min):
```cron
*/30 * * * * cd /path/to/pokeAPI && /usr/bin/python3 run.py
```

**Hermes cron** (if you use Hermes):
```bash
hermes schedule "*/30 7-21 * * *" \
  --profile verde \
  --target telegram \
  --script ~/pokeAPI/run.py \
  --no-agent \
  --name "pokemon-stock-check"
```

## Products Tracked

Currently tracks all main Target TCINs and Best Buy SKUs for:
- 151 Booster Bundle / Booster Pack / Poster Collection / ETB
- Prismatic Evolutions ETB / Booster Bundle / Poster Collection
- Surging Sparks Booster Bundle / ETB
- Twilight Masquerade Booster Bundle
- Paldean Fates Booster Bundle / ETB

Edit `tracker/products.py` to customize.

## Commands

```bash
python run.py                          # Full check
python run.py --target-only            # Target only
python run.py --bestbuy-only           # Best Buy only
python run.py --pattern-report         # Show observed restock patterns
```
