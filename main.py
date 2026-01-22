import os
import json
import requests
from bs4 import BeautifulSoup
import sys
from datetime import datetime

# --- CONFIGURAZIONE ---
URL = "https://management.lum.it/bandi-e-avvisi/"
HISTORY_FILE = "history.json"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

TG_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_alert(message):
    if not TG_TOKEN or not TG_CHAT_ID:
        print("[!] Errore: Token o Chat ID mancanti.")
        return
    
    send_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        requests.post(send_url, data=payload)
    except Exception as e:
        print(f"[!] Errore invio Telegram: {e}")

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(data):
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=4)

def check_lum():
    print(f"[*] Avvio scansione LUM Sniper su: {URL}")
    
    try:
        response = requests.get(URL, headers=HEADERS, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"[!] Errore connessione sito: {e}")
        sys.exit(1)

    soup = BeautifulSoup(response.text, 'html.parser')
    active_tags = soup.find_all('span', class_='status-active')
    
    current_active_urls = []
    history = load_history()

    print(f"[*] Trovati {len(active_tags)} bandi attivi totali.")

    for tag in active_tags:
        card = tag.find_parent('div')
        while card and len(card.get_text(strip=True)) < 20:
            card = card.find_parent('div')
            
        if not card: continue

        link_tag = card.find('a', href=True)
        link = link_tag['href'] if link_tag else "N/A"
        
        if link == "N/A": continue
        
        current_active_urls.append(link)

        # SE È NUOVO
        if link not in history:
            title_tag = card.find(['h3', 'h4', 'h5', 'h6'])
            title = title_tag.get_text(strip=True) if title_tag else "Nuovo Bando"
            if title == "Nuovo Bando":
                 title = " ".join(card.get_text().split())[:60] + "..."

            print(f"🚀 NUOVO BANDO RILEVATO: {title}")
            
            # DATA CORRETTA CALCOLATA IN PYTHON
            now_str = datetime.now().strftime("%d/%m/%Y alle %H:%M")
            
            msg = (
                f"🎯 <b>NUOVO BANDO LUM ATTIVO!</b>\n\n"
                f"📝 <b>{title}</b>\n"
                f"🔗 <a href='{link}'>Clicca qui per candidarti subito</a>\n\n"
                f"<i>Rilevato il: {now_str}</i>"
            )
            send_telegram_alert(msg)
        else:
            print(f" -> Già in memoria: {link}")

    if set(current_active_urls) != set(history):
        save_history(current_active_urls)
        print("[*] Database aggiornato.")
    else:
        print("[*] Nessuna variazione.")

if __name__ == "__main__":
    check_lum()
