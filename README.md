# 🇹🇷 Turkish Vocabulary Daily Email

Sends a daily email with a CEFR-leveled Turkish word including:
- Definition from Wiktionary
- Etymology from Wiktionary (when available)
- Real example sentence from Tatoeba (skipped if none found)

No AI API required — all data comes from free public sources.
Email delivery via Resend (free tier: 3,000 emails/month).

---

## Setup

### 1. Get a Resend API Key

1. Sign up at https://resend.com
2. Go to **API Keys** → create a new key
3. Copy it

### 2. Sender address

- **Quick start:** use `onboarding@resend.dev` as FROM_EMAIL — works immediately on the free tier but can only send to your own verified email
- **Custom domain:** add and verify your domain in the Resend dashboard, then use any address at that domain

### 3. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/turkish-vocab-email.git
git push -u origin main
```

### 4. Deploy on Railway

1. Go to https://railway.app → **New Project** → **Deploy from GitHub repo**
2. Select your repo — Railway detects the `Dockerfile` automatically
3. Go to **Variables** and add:

| Variable | Value |
|---|---|
| `RESEND_API_KEY` | your key from resend.com |
| `FROM_EMAIL` | e.g. onboarding@resend.dev or vocab@yourdomain.com |
| `TO_EMAIL` | where you want to receive the emails |
| `CEFR_LEVEL` | `C1` (or `A1`, `A2`, `B1`, `B2`) |

4. Railway reads `railway.toml` and runs the script as a cron job at **7:00 AM UTC** daily.

### 5. Change the send time

Edit `railway.toml`:
```toml
cronSchedule = "0 15 * * *"  # e.g. 3:00 PM UTC = 8:00 AM Pacific
```
Use https://crontab.guru to find your preferred time.

---

## Local Testing

```bash
export RESEND_API_KEY="re_..."
export FROM_EMAIL="onboarding@resend.dev"
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
- **Resend** — email delivery API (free tier: 3,000 emails/month)
