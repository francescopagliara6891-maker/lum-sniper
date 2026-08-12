import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
from urllib.parse import urljoin

# ---------------------------------------------------------
# 🎯 CONFIGURAZIONE
# ---------------------------------------------------------
HISTORY_FILE = "history.json"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

TG_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Ottieni l'anno corrente per filtrare le cianfrusaglie
CURRENT_YEAR = str(datetime.now(pytz.utc).year)       # "2026"
NEXT_YEAR = str(datetime.now(pytz.utc).year + 1)      # "2027"
ACADEMIC_YEAR = f"{CURRENT_YEAR}/{NEXT_YEAR}"         # "2026/2027"

def send_telegram_alert(message):
    if not TG_TOKEN or not TG_CHAT_ID: return
    send_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "HTML", "disable_web_page_preview": False}
    try: requests.post(send_url, data=payload)
    except: pass

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f: return json.load(f)
        except: pass
    return []

def save_history(data):
    with open(HISTORY_FILE, "w") as f:
        json.dump(list(set(data)), f, indent=4)

def get_rome_time():
    return datetime.now(pytz.utc).astimezone(pytz.timezone('Europe/Rome')).strftime("%d/%m/%Y alle %H:%M")

# ---------------------------------------------------------
# 🔬 MOTORE 1: IL BISTURI (Solo per LUM) - La tua logica originale
# ---------------------------------------------------------
def check_lum_surgical(history):
    print("[*] Esecuzione Bisturi su LUM...")
    nuovi_link = []
    
    # 1. LUM MASTER E CORSI
    try:
        res = requests.get("https://management.lum.it/bandi-e-avvisi/", headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Cerca solo i badge "Attivo"
        active_badges = soup.find_all(lambda tag: tag.name in ['span', 'div', 'p', 'h4', 'h5', 'h6', 'b', 'strong'] and tag.get_text(strip=True).lower() == 'attivo')
        
        for badge in active_badges:
            card = badge
            for _ in range(6):
                if card.parent: card = card.parent
                else: break
                    
            title_tag = card.find(['h3', 'h4', 'h5', 'h6', 'h2'])
            title = title_tag.get_text(strip=True) if title_tag else "Bando LUM"
            
            links = card.find_all('a', href=True)
            valid_link = next((a['href'].strip() for a in links if a['href'].strip() != "https://management.lum.it/bandi-e-avvisi/" and not a['href'].startswith('#')), None)
            
            if not valid_link: continue

            # La Ghigliottina
            testo = (title + " " + valid_link).lower()
            if any(p in testo for p in ['job-placement', 'job placement']) and not any(s in testo for s in ['master', 'executive']):
                continue

            if valid_link not in history:
                nuovi_link.append(valid_link)
                msg = f"🎯 <b>NUOVO BANDO LUM ATTIVO!</b>\n\n📝 <b>{title}</b>\n🔗 <a href='{valid_link}'>Apri Bando</a>\n\n<i>Rilevato il: {get_rome_time()}</i>"
                send_telegram_alert(msg)
                
    except Exception as e: print(f"[!] Errore LUM Master: {e}")

    # 2. LUM JOBS
    try:
        res = requests.get("https://www.lum.it/job-opportunities/", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        for span in soup.find_all('span'):
            if "aperto" in span.get_text(strip=True).lower():
                card = span.find_parent(['div', 'article', 'li'])
                if card and card.find('a', href=True):
                    link = urljoin("https://www.lum.it", card.find('a')['href'])
                    if link not in history and link not in nuovi_link:
                        nuovi_link.append(link)
                        msg = f"💼 <b>[LUM] NUOVA OFFERTA DI LAVORO!</b>\n🔗 <a href='{link}'>Vedi offerta</a>\n\n<i>Rilevata il: {get_rome_time()}</i>"
                        send_telegram_alert(msg)
    except Exception as e: print(f"[!] Errore LUM Jobs: {e}")

    return nuovi_link


# ---------------------------------------------------------
# 📡 MOTORE 2: IL RADAR (Con Filtro Temporale 2026/2027)
# ---------------------------------------------------------
def check_radar_targets(history):
    print("[*] Esecuzione Radar Temporale...")
    
    TARGETS = {
        "UNIBA_Formazione": "https://www.uniba.it/it/didattica/corsi-universitari-di-formazione-finalizzata/corsi-e-progetti-di-alta-formazione",
        "UNIBA_Jonico": "https://www.uniba.it/it/ricerca/dipartimenti/sistemi-giuridici-ed-economici",
        "Sistema_Puglia": "https://www.sistema.puglia.it/SistemaPuglia/formazione",
        "Regione_Puglia": "https://por.regione.puglia.it/it/bandi",
        "ARESS_Puglia": "https://www.sanita.puglia.it/web/aress/news-in-primo-piano"
    }

    # Le parole che cerchiamo nel titolo del link
    TRIGGER_WORDS = ["short master", "master", "borsa di studio", "gratuito", "online", "da remoto", "pass laureati", "ritorno al futuro", "migrazioni", "patti territoriali", "cyber"]
    
    nuovi_link = []

    for site, url in TARGETS.items():
        try:
            res = requests.get(url, headers=HEADERS, timeout=20)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            for tag in soup.find_all('a', href=True):
                testo_link = tag.get_text(strip=True).lower()
                href = tag['href'].strip()
                link_assoluto = urljoin(url, href)
                
                # REGOLE DI INGAGGIO RIGIDE:
                # 1. Il link deve contenere almeno una parola chiave
                if not any(kw in testo_link for kw in TRIGGER_WORDS):
                    continue
                    
                # 2. DEVE contenere riferimenti all'anno corrente/successivo, oppure parole chiave stringenti come "bando aperto" / "avviso pubblico"
                if CURRENT_YEAR not in testo_link and NEXT_YEAR not in testo_link and ACADEMIC_YEAR not in testo_link and "aperto" not in testo_link and "avviso" not in testo_link:
                    continue

                # 3. Elimina archivi palesi
                if any(old in testo_link or old in href for old in ["2021", "2022", "2023", "2024", "2025", "archivio", "scadut", "graduatoria"]):
                    continue

                if link_assoluto not in history and link_assoluto not in nuovi_link:
                    nuovi_link.append(link_assoluto)
                    titolo = tag.get_text(strip=True)
                    msg = f"🎯 <b>SNIPER ALERT: {site}</b>\n\n📝 <b>{titolo}</b>\n🔗 <a href='{link_assoluto}'>Apri la pagina</a>\n\n<i>Rilevato il: {get_rome_time()}</i>"
                    send_telegram_alert(msg)
                    
        except Exception as e:
            print(f"[!] Errore su {site}: {e}")

    return nuovi_link

# ---------------------------------------------------------
# 🚀 ESECUZIONE
# ---------------------------------------------------------
if __name__ == "__main__":
    storico_attuale = load_history()
    
    nuovi_lum = check_lum_surgical(storico_attuale)
    nuovi_radar = check_radar_targets(storico_attuale)
    
    tutti_i_nuovi = nuovi_lum + nuovi_radar
    
    if tutti_i_nuovi:
        save_history(storico_attuale + tutti_i_nuovi)
        print(f"[*] Database aggiornato con {len(tutti_i_nuovi)} nuovi elementi.")
    else:
        print("[*] Nessun nuovo bersaglio. Tutto tranquillo.")
