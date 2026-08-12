import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
from urllib.parse import urljoin # Fondamentale per i siti che usano link relativi (es. /bando-123)

# ---------------------------------------------------------
# 🎯 CONFIGURAZIONE DEL CECCHINO (OMNI-SNIPER)
# ---------------------------------------------------------
HISTORY_FILE = "history.json"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

TG_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 🌐 L'ARSENALE DEI BERSAGLI (Aggiungi qui qualsiasi sito vuoi!)
TARGETS = {
    "LUM_Avvisi": "https://management.lum.it/bandi-e-avvisi/",
    "LUM_Jobs": "https://www.lum.it/job-opportunities/",
    "UNIBA_AltaForm": "https://www.uniba.it/it/didattica/corsi-universitari-di-formazione-finalizzata/corsi-e-progetti-di-alta-formazione",
    "UNIBA_Albo": "https://www.uniba.it/it/ateneo/albo-pretorio",
    "UNIBA_Jonico": "https://www.uniba.it/it/ricerca/dipartimenti/sistemi-giuridici-ed-economici", # Sede dei master su migrazioni/antimafia
    "Sistema_Puglia": "https://www.sistema.puglia.it/SistemaPuglia/formazione",
    "ARESS_Puglia": "https://www.sanita.puglia.it/web/aress/news-in-primo-piano",
    "Regione_Puglia": "https://por.regione.puglia.it/it/bandi"
}

# 🔫 I GRILLETTI: Parole che fanno scattare la notifica
TRIGGER_WORDS = [
    "short master", "master", "alta formazione", "borsa di studio", 
    "gratuito", "finanziato", "fad ", "online", "da remoto", "e-learning",
    "pass laureati", "ritorno al futuro", "patti territoriali",
    "migrazioni", "mediazione", "cyber security", "inps", "inclusione"
]

# 🔕 I SILENZIATORI: Scarta graduatorie, esiti e roba vecchia
KILL_WORDS = [
    "scaduto", "graduatoria", "esit", "commissione", "convocazione", 
    "aggiudicazione", "rinvio", "errata corrige"
]

def send_telegram_alert(message):
    if not TG_TOKEN or not TG_CHAT_ID: return
    send_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "HTML", "disable_web_page_preview": False}
    try: requests.post(send_url, data=payload)
    except: pass

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list): return data
        except: pass
    return []

def save_history(data):
    with open(HISTORY_FILE, "w") as f:
        json.dump(list(set(data)), f, indent=4)

def get_rome_time():
    return datetime.now(pytz.utc).astimezone(pytz.timezone('Europe/Rome')).strftime("%d/%m/%Y alle %H:%M")

def universal_sniper_engine(history):
    print("[*] Avvio OMNI-SNIPER. Inizializzazione motore universale...")
    now_str = get_rome_time()
    nuovi_link_trovati = []

    for site_name, base_url in TARGETS.items():
        print(f"[*] Puntamento su: {site_name} -> {base_url}")
        try:
            res = requests.get(base_url, headers=HEADERS, timeout=20)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Cattura TUTTI i link della pagina
            links = soup.find_all('a', href=True)
            
            for tag in links:
                testo_link = tag.get_text(strip=True).lower()
                href_grezzo = tag['href'].strip()
                
                # Unisce base_url e href parziale per creare il link assoluto e funzionante
                link_assoluto = urljoin(base_url, href_grezzo)
                testo_da_analizzare = f"{testo_link} {link_assoluto}".lower()

                # Ignora ancore, mailto e link spazzatura generici
                if not href_grezzo or href_grezzo.startswith('#') or 'mailto:' in href_grezzo:
                    continue

                # 1. Controlla i silenziatori (se c'è una kill_word, salta al prossimo link)
                if any(kw in testo_da_analizzare for kw in KILL_WORDS):
                    continue

                # 2. Controlla i grilletti (o se è il sito Job Placement LUM che va sempre segnalato)
                is_target = any(kw in testo_da_analizzare for kw in TRIGGER_WORDS)
                if site_name == "LUM_Jobs" and "aperto" in testo_link: 
                    is_target = True
                
                if is_target:
                    if link_assoluto not in history and link_assoluto not in nuovi_link_trovati:
                        nuovi_link_trovati.append(link_assoluto)
                        titolo_pulito = tag.get_text(strip=True)
                        if not titolo_pulito: titolo_pulito = "Avviso/Bando (Titolo non testuale)"
                        
                        msg = (
                            f"🎯 <b>SNIPER ALERT: {site_name}</b>\n\n"
                            f"📝 <b>{titolo_pulito}</b>\n"
                            f"🔗 <a href='{link_assoluto}'>Apri la pagina</a>\n\n"
                            f"<i>Rilevato il: {now_str}</i>"
                        )
                        send_telegram_alert(msg)
                        print(f"🚀 COLPO A SEGNO su {site_name}: {titolo_pulito}")

        except Exception as e:
            print(f"[!] Target {site_name} fuori portata o in errore: {e}")

    return nuovi_link_trovati

if __name__ == "__main__":
    storico_attuale = load_history()
    nuove_scoperte = universal_sniper_engine(storico_attuale)
    
    if nuove_scoperte:
        storico_aggiornato = list(set(storico_attuale + nuove_scoperte))
        save_history(storico_aggiornato)
        print(f"[*] Database aggiornato. {len(nuove_scoperte)} nuovi target colpiti.")
    else:
        print("[*] Nessun nuovo bersaglio. Mimetizzazione in corso...")
