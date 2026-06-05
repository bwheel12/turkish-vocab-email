#!/usr/bin/env python3
"""
Turkish Daily Vocabulary Email
Sends a daily vocabulary email based on CEFR level using Gmail SMTP.
Definitions and etymology from Wiktionary; example sentences from Tatoeba.
No AI API required.
"""

import json
import os
import random
import re
import urllib.request
import urllib.parse
import urllib.error
from datetime import date


# ── Configuration (set via environment variables) ────────────────────────────
CEFR_LEVEL   = os.environ.get("CEFR_LEVEL", "C1")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
FROM_EMAIL   = os.environ.get("FROM_EMAIL")   # e.g. vocab@yourdomain.com
TO_EMAIL     = os.environ.get("TO_EMAIL")


# ── Load word list ────────────────────────────────────────────────────────────
def load_words(level: str) -> list[str]:
    path = os.path.join(os.path.dirname(__file__), f"words_{level.lower()}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def pick_word(words: list[str]) -> str:
    rng = random.Random(date.today().isoformat())
    return rng.choice(words)


# ── Wiktionary ────────────────────────────────────────────────────────────────
def fetch_wiktionary(word: str) -> dict:
    """
    Fetch definition, etymology, and page URL from English Wiktionary.
    Uses the REST summary API plus the wikitext API for etymology extraction.
    Returns a dict with keys: definition, etymology, page_url.
    All values may be empty strings if not found.
    """
    encoded = urllib.parse.quote(word)
    result = {"definition": "", "etymology": "", "page_url": ""}

    # --- Summary (definition) ---
    summary_url = f"https://en.wiktionary.org/api/rest_v1/page/summary/{encoded}"
    try:
        req = urllib.request.Request(
            summary_url, headers={"User-Agent": "TurkishVocabBot/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            result["definition"] = data.get("extract", "")
            result["page_url"] = (
                data.get("content_urls", {}).get("desktop", {}).get("page", "")
            )
    except Exception:
        pass

    # --- Wikitext (etymology) ---
    wikitext_url = (
        f"https://en.wiktionary.org/w/api.php?action=parse&page={encoded}"
        f"&prop=wikitext&format=json"
    )
    try:
        req = urllib.request.Request(
            wikitext_url, headers={"User-Agent": "TurkishVocabBot/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")

        # Find the Turkish section, then look for an Etymology subsection
        turkish_match = re.search(
            r"==Turkish==(.+?)(?=\n==[^=]|\Z)", wikitext, re.DOTALL
        )
        if turkish_match:
            turkish_section = turkish_match.group(1)
            etym_match = re.search(
                r"===Etymology.*?===\s*(.+?)(?=\n===|\Z)", turkish_section, re.DOTALL
            )
            if etym_match:
                raw = etym_match.group(1).strip()
                # Strip wikitext markup: {{...}}, [[...]], ''...''
                raw = re.sub(r"\{\{[^}]*\}\}", "", raw)
                raw = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", raw)
                raw = re.sub(r"'{2,3}", "", raw)
                raw = re.sub(r"<[^>]+>", "", raw)
                raw = re.sub(r"\s+", " ", raw).strip()
                if raw:
                    result["etymology"] = raw
    except Exception:
        pass

    return result


# ── Tatoeba ───────────────────────────────────────────────────────────────────
def fetch_tatoeba(word: str) -> dict:
    """
    Search Tatoeba for a Turkish sentence containing the word.
    Returns dict with keys: turkish, english (both may be empty if not found).
    """
    encoded = urllib.parse.quote(word)
    url = (
        f"https://tatoeba.org/en/api_v0/search"
        f"?query={encoded}&from=tur&to=eng&trans_filter=limit&limit=10"
    )
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "TurkishVocabBot/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        results = data.get("results", [])
        for item in results:
            turkish_text = item.get("text", "")
            # Look for an English translation
            for translation_group in item.get("translations", []):
                for t in translation_group:
                    if t.get("lang") == "eng":
                        return {
                            "turkish": turkish_text,
                            "english": t.get("text", ""),
                        }
    except Exception:
        pass

    return {"turkish": "", "english": ""}


# ── HTML email template ───────────────────────────────────────────────────────
def build_html(word: str, wikt: dict, tatoeba: dict, level: str) -> str:
    today = date.today().strftime("%B %d, %Y")

    wikt_link = (
        f'<a href="{wikt["page_url"]}" style="color:#6b7280;font-size:12px;">'
        f"Wiktionary entry ↗</a>"
        if wikt["page_url"]
        else ""
    )

    # Etymology block — only rendered if we have content
    etymology_block = ""
    if wikt["etymology"] or wikt["definition"]:
        etym_text = wikt["etymology"] or wikt["definition"]
        etymology_block = f"""
    <tr>
      <td style="padding:28px 36px 0;">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="background:#f8f7ff;border-left:3px solid #a78bfa;padding:16px 20px;border-radius:0 6px 6px 0;">
              <p style="margin:0 0 6px;color:#a78bfa;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;font-family:Arial,sans-serif;">Word Origin</p>
              <p style="margin:0;font-size:14px;color:#374151;line-height:1.7;font-family:Arial,sans-serif;">{etym_text}</p>
              <p style="margin:10px 0 0;">{wikt_link}</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>"""

    # Example sentence block — only rendered if Tatoeba found something
    example_block = ""
    if tatoeba["turkish"]:
        example_block = f"""
    <tr>
      <td style="padding:28px 36px 0;">
        <p style="margin:0 0 10px;color:#a78bfa;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;font-family:Arial,sans-serif;">In Use</p>
        <p style="margin:0;font-size:16px;color:#1a1a2e;line-height:1.8;font-style:italic;">"{tatoeba['turkish']}"</p>
        {"<p style=\\"margin:10px 0 0;font-size:14px;color:#6b7280;line-height:1.7;font-family:Arial,sans-serif;\\">&ldquo;" + tatoeba['english'] + "&rdquo;</p>" if tatoeba['english'] else ""}
        <p style="margin:8px 0 0;color:#9ca3af;font-size:12px;font-family:Arial,sans-serif;">— Tatoeba</p>
      </td>
    </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Turkish Word of the Day</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f0;font-family:Georgia,serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f0;padding:32px 16px;">
  <tr><td align="center">
  <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

    <!-- Header -->
    <tr>
      <td style="background:#1a1a2e;padding:28px 36px;">
        <p style="margin:0;color:#a78bfa;font-size:12px;letter-spacing:2px;text-transform:uppercase;font-family:Arial,sans-serif;">Turkish · Word of the Day</p>
        <p style="margin:6px 0 0;color:#e5e7eb;font-size:13px;font-family:Arial,sans-serif;">{today} &nbsp;·&nbsp; CEFR {level}</p>
      </td>
    </tr>

    <!-- Word -->
    <tr>
      <td style="padding:36px 36px 0;">
        <h1 style="margin:0;font-size:48px;color:#1a1a2e;font-weight:normal;letter-spacing:-1px;">{word}</h1>
      </td>
    </tr>

    <!-- Divider -->
    <tr><td style="padding:20px 36px 0;"><hr style="border:none;border-top:1px solid #e5e7eb;"></td></tr>

    <!-- Definition -->
    <tr>
      <td style="padding:24px 36px 0;">
        <p style="margin:0 0 4px;color:#a78bfa;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;font-family:Arial,sans-serif;">Definition</p>
        <p style="margin:0;font-size:17px;color:#1a1a2e;line-height:1.6;">{wikt["definition"] or "See Wiktionary for details."}</p>
      </td>
    </tr>

    {etymology_block}
    {example_block}

    <!-- Footer -->
    <tr>
      <td style="padding:36px 36px 32px;">
        <hr style="border:none;border-top:1px solid #e5e7eb;margin-bottom:20px;">
        <p style="margin:0;color:#9ca3af;font-size:12px;font-family:Arial,sans-serif;text-align:center;">
          Turkish Vocabulary · CEFR {level} · Daily series
        </p>
      </td>
    </tr>

  </table>
  </td></tr>
</table>
</body>
</html>"""


def build_plain(word: str, wikt: dict, tatoeba: dict, level: str) -> str:
    today = date.today().strftime("%B %d, %Y")
    lines = [
        f"Turkish Word of the Day — {today} (CEFR {level})",
        "=" * 50,
        "",
        word.upper(),
        "",
    ]
    if wikt["definition"]:
        lines += ["DEFINITION", wikt["definition"], ""]
    if wikt["etymology"]:
        lines += ["WORD ORIGIN", wikt["etymology"], ""]
    if tatoeba["turkish"]:
        lines += ["IN USE", f'"{tatoeba["turkish"]}"']
        if tatoeba["english"]:
            lines.append(f'"{tatoeba["english"]}"')
        lines += ["— Tatoeba", ""]
    if wikt["page_url"]:
        lines += [f"Wiktionary: {wikt['page_url']}"]
    return "\n".join(lines)


# ── Send email ────────────────────────────────────────────────────────────────
def send_email(subject: str, html: str, plain: str):
    payload = json.dumps({
        "from": FROM_EMAIL,
        "to": [TO_EMAIL],
        "subject": subject,
        "html": html,
        "text": plain,
    }).encode()

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {RESEND_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode())
    print(f"✓ Email sent to {TO_EMAIL} (id: {result.get('id', '?')})")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not all([RESEND_API_KEY, FROM_EMAIL, TO_EMAIL]):
        raise EnvironmentError(
            "Missing required env vars: RESEND_API_KEY, FROM_EMAIL, TO_EMAIL"
        )

    print(f"→ Loading {CEFR_LEVEL} word list...")
    words = load_words(CEFR_LEVEL)
    word  = pick_word(words)
    print(f"→ Today's word: {word}")

    print("→ Fetching Wiktionary...")
    wikt = fetch_wiktionary(word)
    print(f"  definition: {'✓' if wikt['definition'] else '✗'}")
    print(f"  etymology:  {'✓' if wikt['etymology'] else '✗'}")

    print("→ Fetching Tatoeba example...")
    tatoeba = fetch_tatoeba(word)
    print(f"  sentence:   {'✓' if tatoeba['turkish'] else '✗ (skipped)'}")

    subject = f"🇹🇷 Turkish Word of the Day: {word} ({CEFR_LEVEL})"
    html    = build_html(word, wikt, tatoeba, CEFR_LEVEL)
    plain   = build_plain(word, wikt, tatoeba, CEFR_LEVEL)

    print("→ Sending email...")
    send_email(subject, html, plain)


if __name__ == "__main__":
    main()
