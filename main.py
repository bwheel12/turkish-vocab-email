#!/usr/bin/env python3
"""
Turkish Daily Vocabulary Email
Sends a daily email with 2 CEFR-leveled Turkish words.
Definitions and etymology from Wiktionary; example sentences from Tatoeba.
Tracks seen words to avoid repeats. No AI API required.
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
CEFR_LEVEL     = os.environ.get("CEFR_LEVEL", "C1")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
FROM_EMAIL     = os.environ.get("FROM_EMAIL")
TO_EMAIL       = os.environ.get("TO_EMAIL")


# ── Load word list ────────────────────────────────────────────────────────────
def load_words(level: str) -> list:
    path = os.path.join(os.path.dirname(__file__), f"words_{level.lower()}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Duplicate tracking ────────────────────────────────────────────────────────
def get_seen_path(level: str) -> str:
    return os.path.join(os.path.dirname(__file__), f"seen_{level.lower()}.json")


def load_seen(level: str) -> set:
    path = get_seen_path(level)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen(level: str, seen: set):
    path = get_seen_path(level)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=2)


def pick_words(words: list, level: str, count: int = 2) -> list:
    seen = load_seen(level)
    available = [w for w in words if w not in seen]

    # If exhausted, reset and start fresh
    if len(available) < count:
        print(f"  -> Word list exhausted, resetting seen words for {level.upper()}")
        seen = set()
        available = list(words)

    rng = random.Random(date.today().isoformat())
    chosen = rng.sample(available, min(count, len(available)))

    seen.update(chosen)
    save_seen(level, seen)
    return chosen


# ── Wiktionary ────────────────────────────────────────────────────────────────
def fetch_wiktionary(word: str) -> dict:
    encoded = urllib.parse.quote(word)
    result = {"definition": "", "etymology": "", "page_url": ""}
    result["page_url"] = f"https://en.wiktionary.org/wiki/{encoded}"

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

        turkish_match = re.search(
            r"==Turkish==(.+?)(?=\n==[^=]|\Z)", wikitext, re.DOTALL
        )
        if not turkish_match:
            return result
        turkish_section = turkish_match.group(1)

        # --- Etymology ---
        etym_match = re.search(
            r"===Etymology[^=]*===\s*\n(.+?)(?=\n===|\Z)", turkish_section, re.DOTALL
        )
        if etym_match:
            raw = etym_match.group(1).strip()
            raw = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", raw)

            def expand_template(m):
                parts = [p.strip() for p in m.group(1).split("|")]
                name = parts[0].lower()
                words_inner = [p for p in parts[1:] if p and not re.match(r'^[a-z]{2,3}$', p) and '=' not in p]
                if name in ("affix", "suffix", "prefix", "confix", "compound"):
                    return " + ".join(words_inner)
                if name in ("der", "inh", "bor", "inherited", "derived", "borrowed"):
                    return words_inner[-1] if words_inner else ""
                if name in ("m", "mention", "l", "link"):
                    return words_inner[-1] if words_inner else ""
                if name in ("surf", "surface analysis"):
                    return "surface analysis: " + " + ".join(words_inner)
                return " ".join(words_inner) if words_inner else ""

            raw = re.sub(r"\{\{([^}]+)\}\}", expand_template, raw)
            raw = re.sub(r"'{2,3}", "", raw)
            raw = re.sub(r"<[^>]+>", "", raw)
            raw = re.sub(r"\s+", " ", raw).strip()
            if raw and len(raw) > 3 and not re.match(r'^[\s.,:;+]+$', raw):
                result["etymology"] = raw

        # --- Definitions ---
        definitions = []
        pos_sections = re.findall(
            r"===(Noun|Verb|Adjective|Adverb|Pronoun|Interjection|Participle|Postposition)[^=]*===\s*\n"
            r"(?:[^#\n][^\n]*\n)*"
            r"((?:#[^:\n][^\n]*\n?)+)",
            turkish_section
        )
        for pos, def_block in pos_sections:
            for line in def_block.splitlines():
                line = line.strip()
                if not line.startswith("#") or line.startswith("#:") or line.startswith("#*"):
                    continue
                defn = line.lstrip("#").strip()
                defn = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", defn)
                defn = re.sub(r"\{\{[^}]*\}\}", "", defn)
                defn = re.sub(r"'{2,3}", "", defn)
                defn = re.sub(r"<[^>]+>", "", defn)
                defn = re.sub(r"\s+", " ", defn).strip()
                if defn and len(defn) > 2:
                    definitions.append(f"({pos.lower()}) {defn}")
        if definitions:
            result["definition"] = "; ".join(definitions[:3])

    except Exception:
        pass

    return result


# ── Tatoeba ───────────────────────────────────────────────────────────────────
def fetch_tatoeba(word: str) -> dict:
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

        for item in data.get("results", []):
            turkish_text = item.get("text", "")
            for translation_group in item.get("translations", []):
                for t in translation_group:
                    if t.get("lang") == "eng":
                        return {"turkish": turkish_text, "english": t.get("text", "")}
    except Exception:
        pass

    return {"turkish": "", "english": ""}


# ── HTML helpers ──────────────────────────────────────────────────────────────
def build_word_card(word: str, wikt: dict, tatoeba: dict) -> str:
    wikt_link = (
        '<a href="' + wikt["page_url"] + '" style="color:#6b7280;font-size:12px;">Wiktionary entry &#x2197;</a>'
        if wikt["page_url"] else ""
    )

    definition_block = ""
    if wikt["definition"]:
        definition_block = (
            '<tr><td style="padding:20px 36px 0;">'
            '<p style="margin:0 0 4px;color:#a78bfa;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;font-family:Arial,sans-serif;">Definition</p>'
            '<p style="margin:0;font-size:17px;color:#1a1a2e;line-height:1.6;">' + wikt["definition"] + '</p>'
            '</td></tr>'
        )

    etymology_block = ""
    if wikt["etymology"] and len(wikt["etymology"]) > 5:
        etymology_block = (
            '<tr><td style="padding:20px 36px 0;">'
            '<table width="100%" cellpadding="0" cellspacing="0"><tr>'
            '<td style="background:#f8f7ff;border-left:3px solid #a78bfa;padding:16px 20px;border-radius:0 6px 6px 0;">'
            '<p style="margin:0 0 6px;color:#a78bfa;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;font-family:Arial,sans-serif;">Word Origin</p>'
            '<p style="margin:0;font-size:14px;color:#374151;line-height:1.7;font-family:Arial,sans-serif;">' + wikt["etymology"] + '</p>'
            '<p style="margin:10px 0 0;">' + wikt_link + '</p>'
            '</td></tr></table>'
            '</td></tr>'
        )
    elif wikt_link:
        etymology_block = '<tr><td style="padding:12px 36px 0;text-align:right;">' + wikt_link + '</td></tr>'

    example_block = ""
    if tatoeba["turkish"]:
        english_p = ""
        if tatoeba["english"]:
            english_p = '<p style="margin:10px 0 0;font-size:14px;color:#6b7280;line-height:1.7;font-family:Arial,sans-serif;">&ldquo;' + tatoeba["english"] + '&rdquo;</p>'
        example_block = (
            '<tr><td style="padding:20px 36px 0;">'
            '<p style="margin:0 0 10px;color:#a78bfa;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;font-family:Arial,sans-serif;">In Use</p>'
            '<p style="margin:0;font-size:16px;color:#1a1a2e;line-height:1.8;font-style:italic;">&ldquo;' + tatoeba["turkish"] + '&rdquo;</p>'
            + english_p +
            '<p style="margin:8px 0 0;color:#9ca3af;font-size:12px;font-family:Arial,sans-serif;">&#8212; Tatoeba</p>'
            '</td></tr>'
        )

    return (
        '<tr><td style="padding:28px 36px 0;">'
        '<h2 style="margin:0;font-size:40px;color:#1a1a2e;font-weight:normal;letter-spacing:-1px;">' + word + '</h2>'
        '</td></tr>'
        + definition_block
        + etymology_block
        + example_block
    )


def build_html_multi(entries: list, level: str) -> str:
    today = date.today().strftime("%B %d, %Y")
    cards = '<tr><td style="padding:20px 36px 0;"><hr style="border:none;border-top:2px solid #e5e7eb;"></td></tr>'.join(
        build_word_card(word, wikt, tatoeba) for word, wikt, tatoeba in entries
    )
    return (
        '<!DOCTYPE html><html lang="en"><head>'
        '<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Turkish Words of the Day</title></head>'
        '<body style="margin:0;padding:0;background:#f5f5f0;font-family:Georgia,serif;">'
        '<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f0;padding:32px 16px;">'
        '<tr><td align="center">'
        '<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">'
        '<tr><td style="background:#1a1a2e;padding:28px 36px;">'
        '<p style="margin:0;color:#a78bfa;font-size:12px;letter-spacing:2px;text-transform:uppercase;font-family:Arial,sans-serif;">Turkish &middot; Words of the Day</p>'
        '<p style="margin:6px 0 0;color:#e5e7eb;font-size:13px;font-family:Arial,sans-serif;">' + today + ' &nbsp;&middot;&nbsp; CEFR ' + level + '</p>'
        '</td></tr>'
        + cards +
        '<tr><td style="padding:36px 36px 32px;">'
        '<hr style="border:none;border-top:1px solid #e5e7eb;margin-bottom:20px;">'
        '<p style="margin:0;color:#9ca3af;font-size:12px;font-family:Arial,sans-serif;text-align:center;">Turkish Vocabulary &middot; CEFR ' + level + ' &middot; Daily series</p>'
        '</td></tr>'
        '</table></td></tr></table></body></html>'
    )


def build_plain_multi(entries: list, level: str) -> str:
    today = date.today().strftime("%B %d, %Y")
    lines = [
        f"Turkish Words of the Day -- {today} (CEFR {level})",
        "=" * 50,
    ]
    for word, wikt, tatoeba in entries:
        lines += ["", word.upper(), ""]
        if wikt["definition"]:
            lines += ["DEFINITION", wikt["definition"], ""]
        if wikt["etymology"]:
            lines += ["WORD ORIGIN", wikt["etymology"], ""]
        if tatoeba["turkish"]:
            lines += ["IN USE", f'"{tatoeba["turkish"]}"']
            if tatoeba["english"]:
                lines.append(f'"{tatoeba["english"]}"')
            lines += ["-- Tatoeba", ""]
        if wikt["page_url"]:
            lines.append(f"Wiktionary: {wikt['page_url']}")
        lines.append("-" * 50)
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
            "User-Agent": "TurkishVocabBot/1.0",
        },
        method="POST",
    )
    print(f"  from:    {FROM_EMAIL}")
    print(f"  to:      {TO_EMAIL}")
    print(f"  api_key: {RESEND_API_KEY[:8]}...")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
        print(f"OK Email sent to {TO_EMAIL} (id: {result.get('id', '?')})")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"FAIL Resend API error {e.code}: {body}")
        raise


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not all([RESEND_API_KEY, FROM_EMAIL, TO_EMAIL]):
        raise EnvironmentError(
            "Missing required env vars: RESEND_API_KEY, FROM_EMAIL, TO_EMAIL"
        )

    print(f"Loading {CEFR_LEVEL} word list...")
    words = load_words(CEFR_LEVEL)
    chosen = pick_words(words, CEFR_LEVEL, count=2)
    print(f"Today's words: {', '.join(chosen)}")

    entries = []
    for word in chosen:
        print(f"\nFetching data for: {word}")
        wikt = fetch_wiktionary(word)
        print(f"  definition: {'OK' if wikt['definition'] else 'MISS'}")
        print(f"  etymology:  {'OK' if wikt['etymology'] else 'MISS'}")
        tatoeba = fetch_tatoeba(word)
        print(f"  sentence:   {'OK' if tatoeba['turkish'] else 'MISS (skipped)'}")
        entries.append((word, wikt, tatoeba))

    words_label = " & ".join(w for w, _, _ in entries)
    subject = f"Turkish Words of the Day: {words_label} ({CEFR_LEVEL})"
    html  = build_html_multi(entries, CEFR_LEVEL)
    plain = build_plain_multi(entries, CEFR_LEVEL)

    print("\nSending email...")
    send_email(subject, html, plain)


if __name__ == "__main__":
    main()
