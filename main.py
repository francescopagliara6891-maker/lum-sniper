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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
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
    print(f"[*] Avvio scansione LUM Sniper (Focus: Master e Formazione) su: {URL}")
    
    try:
        response = requests.get(URL, headers=HEADERS, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"[!] Errore connessione sito: {e}")
        sys.exit(1)

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # RADAR VISIVO: Cerca ovunque la parola "Attivo" (ignorando maiuscole/minuscole)
    # Copre span, div, p, h3, h4, h5. Impossibile che sfugga.
    active_badges = soup.find_all(lambda tag: tag.name in ['span', 'div', 'p', 'h4', 'h5', 'h6', 'b', 'strong'] and tag.get_text(strip=True).lower() == 'attivo')
    
    current_active_urls = []
    history = load_history()

    print(f"[*] Trovati {len(active_badges)} indicatori di attività. Filtraggio in corso...")

    for badge in active_badges:
        card = badge
        # Risalita per incapsulare l'intero blocco dell'annuncio
        for _ in range(6):
            if card.parent:
                card = card.parent
            else:
                break
                
        # Estrai titolo
        title_tag = card.find(['h3', 'h4', 'h5', 'h6', 'h2'])
        title = title_tag.get_text(strip=True) if title_tag else "Nuovo Bando LUM"
        
        # Estrai tutti i link
        links = card.find_all('a', href=True)
        valid_link = None
        
        for a in links:
            href = a['href'].strip()
            # Ignora link spazzatura (social, mail, link alla pagina stessa)
            if href and href != URL and not href.endswith('#') and 'mailto:' not in href and 'facebook' not in href and 'linkedin' not in href:
                valid_link = href
                # Se è palesemente un bando/master, smettiamo di cercare altri link in questa card
                if any(kw in href.lower() for kw in ['/bando/', '/master/', '/corso/', '/executive/']):
                    break 

        if not valid_link:
            continue

        # --- LA GHIGLIOTTINA (Addio Job Placement) ---
        testo_analisi = (title + " " + valid_link).lower()
        parole_spazzatura = ['job-placement', 'job placement', 'offerta di lavoro', 'assunzione', 'cercasi', 'career']
        
        # Se trova una parola legata al Job Placement, uccide l'annuncio...
        is_job = any(parola in testo_analisi for parola in parole_spazzatura)
        # ... A MENO CHE non sia palesemente un master (Es: "Master in diritto del Lavoro")
        is_safe = any(salvagente in testo_analisi for salvagente in ['master', 'executive', 'corso', 'bando', 'program'])
        
        if is_job and not is_safe:
            print(f"🚯 ELIMINATO (Job Placement ignoto): {title}")
            continue

        # SE PASSA TUTTI I FILTRI ED È NUOVO
        current_active_urls.append(valid_link)

        if valid_link not in history:
            history.append(valid_link) 
            
            print(f"🚀 NUOVA OPPORTUNITÀ RILEVATA: {title}")
            
            utc_now = datetime.now(pytz.utc) 
            rome_tz = pytz.timezone('Europe/Rome') 
            rome_now = utc_now.astimezone(rome_tz) 
            now_str = rome_now.strftime("%d/%m/%Y alle %H:%M")
            
            msg = (
                f"🎯 <b>NUOVO CORSO/MASTER LUM ATTIVO!</b>\n\n"
                f"📝 <b>{title}</b>\n"
                f"🔗 <a href='{valid_link}'>Clicca qui per il bando</a>\n\n"
                f"<i>Rilevato il: {now_str}</i>"
            )
            send_telegram_alert(msg)

    # Sincronizza il radar
    save_history(current_active_urls)
    print("[*] Controllo terminato. Radar sincronizzato sui soli Corsi/Master.")

if __name__ == "__main__":
    check_lum()
