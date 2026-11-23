import os
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

# ==========================================
# KONFIGURASI (Diambil dari GitHub Secrets / Environment Variable)
# ==========================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "ISI_GEMINI_API_KEY")
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "ISI_FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN", "ISI_FB_PAGE_ACCESS_TOKEN")

GRAPH_API_VERSION = "v21.0"
WIB = ZoneInfo("Asia/Jakarta")

# ==========================================
# DAFTAR TOPIK / PRODUK (Dirotasi otomatis tiap jam)
# Silakan ganti sesuai kebutuhan konten FB Page kamu.
# ==========================================
CONTENT_ITEMS = [
    {
        "mode": "Afiliasi",
        "topic": "Panci mini stainless steel SUS 304 gagang kayu 16cm, cepat panas, pas buat masak mie, kuah, atau MPASI porsi kecil, harga promo terjangkau.",
        "link": "",
        "mood": "Ulasan Jujur",
        "style": "Santai Natural",
        "audience": "Anak kos, ibu rumah tangga, pekerja",
    },
    {
        "mode": "Organik",
        "topic": "Kebiasaan kecil yang bikin produktivitas pagi lebih stabil tanpa buru-buru.",
        "link": "",
        "mood": "Tips Edukasi",
        "style": "Akrab / Kasual",
        "audience": "Kreator dan pekerja harian",
    },
    {
        "mode": "Afiliasi",
        "topic": "Lampu meja LED lipat sentuh 3 mode cahaya, hemat daya, nyaman buat kerja/baca malam tanpa bikin mata cepat lelah.",
        "link": "",
        "mood": "Problem - Solution",
        "style": "Santai Natural",
        "audience": "Mahasiswa, freelancer, pekerja WFH",
    },
    {
        "mode": "Bisnis",
        "topic": "Kemasan custom dan hampers rapi untuk bikin produk terlihat lebih bernilai dan siap kirim.",
        "link": "",
        "mood": "Hook Mengejutkan",
        "style": "Informatif",
        "audience": "Pemilik UMKM dan seller online",
    },
]


def get_time_context(now_wib: datetime) -> dict:
    hour = now_wib.hour
    if 7 <= hour <= 10:
        return {
            "slot": "Pagi",
            "vibe": "Segar, ringkas, membangkitkan semangat awal hari, cocok untuk rutinitas/persiapan.",
        }
    elif 11 <= hour <= 14:
        return {
            "slot": "Siang",
            "vibe": "Praktis, langsung ke inti, cocok untuk jeda istirahat siang dan solusi cepat.",
        }
    elif 15 <= hour <= 18:
        return {
            "slot": "Sore",
            "vibe": "Santai, reflektif atau ulasan santai menjelang pulang/waktu luang.",
        }
    else:
        return {
            "slot": "Malam",
            "vibe": "Tenang, bercerita/storytelling, santai menemani waktu istirahat malam.",
        }


def select_item_for_hour(now_wib: datetime) -> dict:
    index = now_wib.hour % len(CONTENT_ITEMS)
    return CONTENT_ITEMS[index]


def build_fb_post(item: dict, ctx: dict, now_wib: datetime) -> str:
    if not GEMINI_API_KEY or GEMINI_API_KEY == "ISI_GEMINI_API_KEY":
        raise ValueError("GEMINI_API_KEY belum diisi.")

    link_line = (
        f"Sertakan link ini secara wajar di bagian akhir/CTA: {item['link']}"
        if item.get("link")
        else "Jangan buat link palsu."
    )

    prompt = f"""Kamu adalah penulis konten media sosial berbahasa Indonesia untuk Facebook Page.
Buat 1 postingan siap tayang yang disesuaikan dengan waktu {ctx['slot']} ({now_wib.strftime('%H:%M')} WIB).

Konteks & Pengaturan:
- Mode: {item['mode']}
- Topik / Produk: {item['topic']}
- Target Audiens: {item['audience']}
- Nuansa Waktu ({ctx['slot']}): {ctx['vibe']}
- Gaya Bahasa: {item['style']}
- Mood: {item['mood']}
- {link_line}

Aturan:
- Awali dengan kalimat pembuka yang menarik perhatian.
- Gunakan paragraf pendek (1-2 kalimat per paragraf) agar nyaman dibaca di layar HP.
- Tutup dengan CTA yang natural dan relevan dengan waktu {ctx['slot']}.
- Jangan tulis teks pembuka/penutup dari AI."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.85},
    }
    res = requests.post(url, json=payload, timeout=30)
    res.raise_for_status()
    data = res.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def publish_fb_page(message: str, link: str = "") -> str:
    if (
        not FB_PAGE_ID
        or FB_PAGE_ID == "ISI_FB_PAGE_ID"
        or not FB_PAGE_ACCESS_TOKEN
        or FB_PAGE_ACCESS_TOKEN == "ISI_FB_PAGE_ACCESS_TOKEN"
    ):
        raise ValueError("FB_PAGE_ID atau FB_PAGE_ACCESS_TOKEN belum diisi.")

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/feed"
    payload = {
        "message": message,
        "access_token": FB_PAGE_ACCESS_TOKEN,
    }
    if link:
        payload["link"] = link

    res = requests.post(url, data=payload, timeout=30)
    res.raise_for_status()
    return res.json().get("id", "")


def main(force_run: bool = False):
    now_wib = datetime.now(WIB)
    hour = now_wib.hour

    if not force_run and (hour < 7 or hour > 21):
        print(f"Lewati: jam sekarang {now_wib.strftime('%H:%M')} WIB (di luar rentang 07.00 - 21.00 WIB).")
        return

    ctx = get_time_context(now_wib)
    item = select_item_for_hour(now_wib)

    print(f"=== Auto-Post FB Page ({now_wib.strftime('%Y-%m-%d %H:%M')} WIB | Slot: {ctx['slot']}) ===")
    fb_text = build_fb_post(item, ctx, now_wib)
    fb_id = publish_fb_page(fb_text, link=item.get("link", ""))
    print(f"[FB Page] Berhasil tayang -> Post ID: {fb_id}")


if __name__ == "__main__":
    main(force_run=False)
