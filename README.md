# 🇹🇷 Turkish Vocabulary Daily Email

Sends a daily email with a CEFR-leveled Turkish word including:
- Definition from Wiktionary
- Etymology from Wiktionary (when available)
- Real example sentence from Tatoeba (skipped if none found)

No AI API required — all data comes from free public sources.

---

## Setup

### 1. Gmail App Password

1. Go to your Google Account → **Security**
2. Make sure **2-Step Verification** is ON
3. Go to https://myaccount.google.com/apppasswords
4. Create a new app password — name it "Turkish Vocab Bot"
5. Copy the 16-character password shown (no spaces)

### 2. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/turkish-vocab-email.git
git push -u origin main
```

### 3. Deploy on Railway

1. Go to https://railway.app → **New Project** → **Deploy from GitHub repo**
2. Select your repo — Railway detects the `Dockerfile` automatically
3. Go to **Variables** and add:

| Variable | Value |
|---|---|
| `GMAIL_USER` | your.email@gmail.com |
| `GMAIL_APP_PW` | your 16-char app password |
| `TO_EMAIL` | recipient email (can be same as GMAIL_USER) |
| `CEFR_LEVEL` | `C1` (or `A1`, `A2`, `B1`, `B2`) |

4. Railway reads `railway.toml` and runs the script as a cron job at **7:00 AM UTC** daily.

### 4. Change the send time

Edit `railway.toml`:
```toml
cronSchedule = "0 15 * * *"  # e.g. 3:00 PM UTC = 8:00 AM Pacific
```
Use https://crontab.guru to find your preferred time.

---

## Local Testing

```bash
export GMAIL_USER="you@gmail.com"
export GMAIL_APP_PW="xxxx xxxx xxxx xxxx"
export TO_EMAIL="you@gmail.com"
export CEFR_LEVEL="C1"

python main.py
```

---

## Word Lists

Word lists live in `words_c1.json` (and `words_a1.json` etc. if you add them).
Each is a plain JSON array of Turkish words.

## Data Sources

- **Wiktionary** — definitions and etymology (free, no key needed)
- **Tatoeba** — real Turkish sentences with English translations (free, no key needed)
