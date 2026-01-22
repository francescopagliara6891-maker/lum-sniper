import os
import json
import requests
from bs4 import BeautifulSoup
import sys

# --- CONFIGURAZIONE ---
URL = "https://management.lum.it/bandi-e-avvisi/"
HISTORY_FILE = "history.json"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Recuperiamo le chiavi dai Segreti di GitHub
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
        # Opzionale: decommenta se vuoi essere avvisato anche se il sito è GIÙ
        # send_telegram_alert(f"⚠️ <b>ALLARME LUM SNIPER</b>\nImpossibile connettersi al sito LUM.\nErrore: {str(e)}")
        sys.exit(1)

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Usiamo il selettore che abbiamo calibrato insieme
    active_tags = soup.find_all('span', class_='status-active')
    
    current_active_urls = []
    new_findings = False
    history = load_history()

    print(f"[*] Trovati {len(active_tags)} bandi attivi totali.")

    for tag in active_tags:
        # Risaliamo al contenitore
        card = tag.find_parent('div')
        while card and len(card.get_text(strip=True)) < 20:
            card = card.find_parent('div')
            
        if not card: continue

        # Estrazione dati
        link_tag = card.find('a', href=True)
        link = link_tag['href'] if link_tag else "N/A"
        
        # Saltiamo se non c'è link (improbabile)
        if link == "N/A": continue
        
        current_active_urls.append(link)

        # CONTROLLO CRUCIALE: È nuovo?
        if link not in history:
            title_tag = card.find(['h3', 'h4', 'h5', 'h6'])
            title = title_tag.get_text(strip=True) if title_tag else "Nuovo Bando (Titolo non rilevato)"
            if title == "Nuovo Bando (Titolo non rilevato)":
                 title = " ".join(card.get_text().split())[:60] + "..."

            print(f"🚀 NUOVO BANDO RILEVATO: {title}")
            
            # Costruiamo il messaggio
            msg = (
                f"🎯 <b>NUOVO BANDO LUM ATTIVO!</b>\n\n"
                f"📝 <b>{title}</b>\n"
                f"🔗 <a href='{link}'>Clicca qui per candidarti subito</a>\n\n"
                f"<i>Rilevato il: {os.environ.get('DATE_NOW', 'Adesso')}</i>"
            )
            send_telegram_alert(msg)
            new_findings = True
        else:
            print(f" -> Già in memoria: {link}")

    # Aggiorniamo lo storico solo con quelli ATTUALMENTE attivi
    # (Così se un bando scade e poi ritorna, viene rinotificato)
    if set(current_active_urls) != set(history):
        save_history(current_active_urls)
        print("[*] Database aggiornato.")
    else:
        print("[*] Nessuna variazione rispetto all'ultimo controllo.")

if __name__ == "__main__":
    check_lum()
