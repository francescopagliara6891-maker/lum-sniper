import os
import json
import requests
from bs4 import BeautifulSoup
import sys
from datetime import datetime
import pytz 

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
    # Salviamo i link attivi, rimuovendo potenziali duplicati
    with open(HISTORY_FILE, "w") as f:
        json.dump(list(set(data)), f, indent=4)

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
        card = tag.parent
        link_tag = None
        levels = 0
        
        # IL MIRINO BLINDATO: Risale la pagina per 6 livelli fino a trovare il link
        while card and levels < 6:
            link_tag = card.find('a', href=True)
            if link_tag:
                break
            card = card.parent
            levels += 1
            
        if not link_tag: 
            continue
            
        link = link_tag['href']
        
        if link == "N/A" or link == "": 
            continue
            
        current_active_urls.append(link)

        # SE IL BANDO È NUOVO PER IL BOT
        if link not in history:
            # Lo aggiungiamo subito alla memoria locale del ciclo
            history.append(link) 
            
            title_tag = card.find(['h3', 'h4', 'h5', 'h6'])
            title = title_tag.get_text(strip=True) if title_tag else "Nuovo Bando"
            if title == "Nuovo Bando":
                 title = " ".join(card.get_text().split())[:60] + "..."

            print(f"🚀 NUOVO BANDO RILEVATO: {title}")
            
            utc_now = datetime.now(pytz.utc) 
            rome_tz = pytz.timezone('Europe/Rome') 
            rome_now = utc_now.astimezone(rome_tz) 
            now_str = rome_now.strftime("%d/%m/%Y alle %H:%M")
            
            msg = (
                f"🎯 <b>NUOVO BANDO LUM ATTIVO!</b>\n\n"
                f"📝 <b>{title}</b>\n"
                f"🔗 <a href='{link}'>Clicca qui per candidarti subito</a>\n\n"
                f"<i>Rilevato il: {now_str}</i>"
            )
            send_telegram_alert(msg)
        else:
            print(f" -> Già in memoria: {link}")

    # Allinea perfettamente la memoria del bot con quello che c'è REALMENTE sul sito.
    # Quando l'università cancella un bando, il bot lo dimenticherà al prossimo giro.
    save_history(current_active_urls)
    print("[*] Controllo terminato. Radar sincronizzato.")

if __name__ == "__main__":
    check_lum()
