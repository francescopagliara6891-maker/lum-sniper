import os
import json
import requests
from bs4 import BeautifulSoup
import sys
from datetime import datetime
import pytz

# --- CONFIGURAZIONE TARGETS ---
URL_LUM = "https://management.lum.it/bandi-e-avvisi/"
URL_UNIBA = "https://www.uniba.it/it/didattica/corsi-universitari-di-formazione-finalizzata/corsi-e-progetti-di-alta-formazione"
URL_ALBO = "https://www.uniba.it/it/ateneo/albo-pretorio"
URL_REGIONE = "https://por.regione.puglia.it/it/bandi"

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
        try:
            with open(HISTORY_FILE, "r") as f:
                # Mantiene la retrocompatibilità col vecchio history.json (che era una lista)
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except:
            pass
    return []

def save_history(data):
    with open(HISTORY_FILE, "w") as f:
        # Usa set per rimuovere eventuali duplicati e salva come lista
        json.dump(list(set(data)), f, indent=4)

def get_rome_time():
    utc_now = datetime.now(pytz.utc) 
    rome_tz = pytz.timezone('Europe/Rome') 
    return utc_now.astimezone(rome_tz).strftime("%d/%m/%Y alle %H:%M")

def check_lum(history):
    print(f"[*] Avvio scansione LUM (Focus: Master e Formazione) su: {URL_LUM}")
    current_active_urls = []
    try:
        response = requests.get(URL_LUM, headers=HEADERS, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        active_badges = soup.find_all(lambda tag: tag.name in ['span', 'div', 'p', 'h4', 'h5', 'h6', 'b', 'strong'] and tag.get_text(strip=True).lower() == 'attivo')
        print(f"[*] LUM: Trovati {len(active_badges)} indicatori di attività.")

        for badge in active_badges:
            card = badge
            for _ in range(6):
                if card.parent: card = card.parent
                else: break
                    
            title_tag = card.find(['h3', 'h4', 'h5', 'h6', 'h2'])
            title = title_tag.get_text(strip=True) if title_tag else "Nuovo Bando LUM"
            
            links = card.find_all('a', href=True)
            valid_link = None
            
            for a in links:
                href = a['href'].strip()
                if href and href != URL_LUM and not href.endswith('#') and 'mailto:' not in href and 'facebook' not in href and 'linkedin' not in href:
                    valid_link = href
                    if any(kw in href.lower() for kw in ['/bando/', '/master/', '/corso/', '/executive/']): break 

            if not valid_link: continue

            # --- LA GHIGLIOTTINA LUM ---
            testo_analisi = (title + " " + valid_link).lower()
            parole_spazzatura = ['job-placement', 'job placement', 'offerta di lavoro', 'assunzione', 'cercasi', 'career']
            is_job = any(parola in testo_analisi for parola in parole_spazzatura)
            is_safe = any(salvagente in testo_analisi for salvagente in ['master', 'executive', 'corso', 'bando', 'program'])
            
            if is_job and not is_safe:
                print(f"🚯 LUM ELIMINATO (Job Placement ignoto): {title}")
                continue

            current_active_urls.append(valid_link)

            if valid_link not in history:
                history.append(valid_link) 
                print(f"🚀 NUOVA OPPORTUNITÀ LUM: {title}")
                now_str = get_rome_time()
                msg = f"🎯 <b>NUOVO CORSO/MASTER LUM ATTIVO!</b>\n\n📝 <b>{title}</b>\n🔗 <a href='{valid_link}'>Clicca qui per il bando</a>\n\n<i>Rilevato il: {now_str}</i>"
                send_telegram_alert(msg)

        return current_active_urls
    except Exception as e:
        print(f"[!] Errore connessione LUM: {e}")
        return []

def check_uniba(history):
    print(f"[*] Avvio scansione UNIBA su: {URL_UNIBA}")
    current_active_urls = []
    try:
        res = requests.get(URL_UNIBA, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        links = soup.find_all('a', href=True)
        
        # Parole chiave espanse in base alle tue richieste
        keywords = ["2026/2027", "2026-2027", "2027", "patti territoriali", "short master", "gratuito", "novità", "bando"]
        
        for link_tag in links:
            testo = link_tag.get_text(strip=True).lower()
            href = link_tag['href'].lower()
            
            if any(kw in testo for kw in keywords) or any(kw in href for kw in keywords):
                link_reale = link_tag['href']
                if not link_reale.startswith('http'):
                    link_reale = "https://www.uniba.it" + link_reale
                    
                current_active_urls.append(link_reale)
                
                if link_reale not in history:
                    history.append(link_reale)
                    titolo_pulito = link_tag.get_text(strip=True)
                    now_str = get_rome_time()
                    msg = f"🎓 <b>[UNIBA] NUOVO CORSO / SHORT MASTER!</b>\n\n📝 <b>{titolo_pulito}</b>\n🔗 <a href='{link_reale}'>Apri la pagina</a>\n\n<i>Rilevato il: {now_str}</i>"
                    send_telegram_alert(msg)
                    
        return current_active_urls
    except Exception as e:
        print(f"[!] Errore UniBa: {e}")
        return []

def check_regione(history):
    print(f"[*] Avvio scansione REGIONE PUGLIA su: {URL_REGIONE}")
    current_active_urls = []
    try:
        res = requests.get(URL_REGIONE, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        links = soup.find_all('a', href=True)
        keywords_regione = ["pass laureati", "alta formazione", "ritorno al futuro", "master"]
        
        for link_tag in links:
            testo = link_tag.get_text(strip=True).lower()
            
            if any(kw in testo for kw in keywords_regione):
                link_reale = link_tag['href']
                if not link_reale.startswith('http'):
                    link_reale = "https://por.regione.puglia.it" + link_reale
                
                current_active_urls.append(link_reale)
                
                if link_reale not in history:
                    history.append(link_reale)
                    titolo_pulito = link_tag.get_text(strip=True)
                    now_str = get_rome_time()
                    msg = f"🏛 <b>[REGIONE PUGLIA] NUOVO BANDO FORMAZIONE!</b>\n\n📝 <b>{titolo_pulito}</b>\n🔗 <a href='{link_reale}'>Apri la pagina</a>\n\n<i>Rilevato il: {now_str}</i>"
                    send_telegram_alert(msg)
                    
        return current_active_urls
    except Exception as e:
         print(f"[!] Errore Regione Puglia: {e}")
         return []

if __name__ == "__main__":
    storico_globale = load_history()
    
    # Esegue tutte le scansioni
    urls_lum = check_lum(storico_globale)
    urls_uniba = check_uniba(storico_globale)
    urls_regione = check_regione(storico_globale)
    
    # Unisce tutti gli URL trovati per mantenere sincronizzato il database
    # In questo modo, se un bando viene rimosso dal sito, non verrà dimenticato e non arriverà una notifica doppia se viene ripubblicato.
    tutti_urls_attuali = urls_lum + urls_uniba + urls_regione
    
    # Assicurati che lo storico contenga sia le nuove scoperte che le vecchie.
    storico_aggiornato = list(set(storico_globale + tutti_urls_attuali))
    
    save_history(storico_aggiornato)
    print(f"[*] Controllo globale terminato. Radar sincronizzato su {len(storico_aggiornato)} elementi totali.")
