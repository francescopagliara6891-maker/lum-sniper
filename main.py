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
    
    # Cattura sia la classe specifica, sia qualunque tag che contenga esplicitamente "Attivo"
    active_tags = soup.find_all('span', class_='status-active')
    for general_tag in soup.find_all(['span', 'div', 'p', 'h5']):
        if general_tag.get_text(strip=True).lower() == 'attivo' and general_tag not in active_tags:
            active_tags.append(general_tag)
    
    current_active_urls = []
    history = load_history()

    print(f"[*] Trovati {len(active_tags)} indicatori di attività. Analisi dei blocchi...")

    for tag in active_tags:
        card = tag.parent
        all_links = []
        title = "Nuovo Bando"
        
        # RISALITA PROFONDA: Raccogliamo TUTTI i link della card per evitare i link-trappola di layout
        for _ in range(7):
            if not card:
                break
            for a in card.find_all('a', href=True):
                href = a['href'].strip()
                # Elimina i link spazzatura che ingannavano la memoria del bot
                if (href and 
                    href != URL and 
                    not href.endswith('#') and 
                    'facebook' not in href and 
                    'linkedin' not in href and 
                    'twitter' not in href and 
                    'mailto:' not in href):
                    if href not in all_links:
                        all_links.append(href)
            
            title_tag = card.find(['h3', 'h4', 'h5', 'h6'])
            if title_tag and title == "Nuovo Bando":
                title = title_tag.get_text(strip=True)
            
            card = card.parent

        if not all_links: 
            continue
            
        # SELEZIONE CHIRURGICA: Cerca il link che porta al bando/master vero e proprio
        best_link = None
        for l in all_links:
            if '/bando/' in l or '/master/' in l or '/corso/' in l:
                best_link = l
                break
        if not best_link:
            best_link = all_links[0]
            
        current_active_urls.append(best_link)

        # --- FILTRO DI ESCLUSIONE JOB PLACEMENT ---
        lowercase_link = best_link.lower()
        lowercase_title = title.lower()
        
        is_job_placement = (
            'job-placement' in lowercase_link or 
            'offerta-di-lavoro' in lowercase_link or 
            'lavoro' in lowercase_link or
            'ricerca di' in lowercase_title or
            'cercasi' in lowercase_title or
            'assunzione' in lowercase_title
        )
        # Protezione per evitare di scartare per errore Master con nomi particolari
        is_academic_training = ('master' in lowercase_title or 'cyber' in lowercase_title or 'executive' in lowercase_title or 'program' in lowercase_title)
        
        if is_job_placement and not is_academic_training:
            print(f"🚯 Saltata offerta Job Placement: {title}")
            continue

        # SE IL BANDO È NUOVO
        if best_link not in history:
            history.append(best_link) 
            
            if title == "Nuovo Bando" and card:
                 title = " ".join(card.get_text().split())[:60] + "..."

            print(f"🚀 NUOVA OPPORTUNITÀ RILEVATA: {title}")
            
            utc_now = datetime.now(pytz.utc) 
            rome_tz = pytz.timezone('Europe/Rome') 
            rome_now = utc_now.astimezone(rome_tz) 
            now_str = rome_now.strftime("%d/%m/%Y alle %H:%M")
            
            msg = (
                f"🎯 <b>NUOVA FORMAZIONE LUM ATTIVA!</b>\n\n"
                f"📝 <b>{title}</b>\n"
                f"🔗 <a href='{best_link}'>Clicca qui per il bando diretto</a>\n\n"
                f"<i>Rilevato il: {now_str}</i>"
            )
            send_telegram_alert(msg)
        else:
            print(f" -> Già in memoria: {best_link}")

    save_history(current_active_urls)
    print("[*] Controllo terminato. Sincronizzazione completata.")

if __name__ == "__main__":
    check_lum()
