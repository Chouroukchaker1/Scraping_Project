from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin

def translate_date(date_text):
    """Traduit les dates de l'anglais au français"""
    if not date_text:
        return date_text
   
    date_text = date_text.strip()
   
    # Traduction des termes courants
    translations = {
        'Today': "Aujourd'hui",
        'Yesterday': 'Hier',
        'Dec': 'Déc',
        'Nov': 'Nov',
        'Jan': 'Jan',
        'Feb': 'Fév',
        'Mar': 'Mar',
        'Apr': 'Avr',
        'May': 'Mai',
        'Jun': 'Juin',
        'Jul': 'Juil',
        'Aug': 'Août',
        'Sep': 'Sept',
        'Oct': 'Oct',
    }
   
    # Traduction des expressions avec "days ago"
    if 'days ago' in date_text.lower():
        days_match = re.search(r'(\d+)\s+days?\s+ago', date_text, re.IGNORECASE)
        if days_match:
            days = days_match.group(1)
            return f"Il y a {days} jour{'s' if int(days) > 1 else ''}"
   
    # Traduction mot par mot
    for eng, fr in translations.items():
        if eng in date_text:
            date_text = date_text.replace(eng, fr)
   
    return date_text

def translate_contract_type(contract_type):
    """Traduit les types de contrat"""
    if not contract_type:
        return contract_type
   
    translations = {
        'Full Time': 'Temps plein',
        'Part Time': 'Temps partiel',
        'Contract': 'Contrat',
        'Consultant': 'Consultant',
        'Temporary': 'Temporaire',
        'Permanent': 'Permanent',
        'Internship': 'Stage',
        'Volunteer': 'Bénévolat'
    }
   
    return translations.get(contract_type, contract_type)

def translate_category(category):
    """Traduit les catégories d'emploi"""
    if not category:
        return category
   
    translations = {
        'Management/leadership': 'Gestion/Leadership',
        'Development': 'Développement',
        'Human Resource And Administration': 'Ressources Humaines et Administration',
        'Consultancies': 'Consultances',
        'Communication/advocacy': 'Communication/Plaidoyer',
        'Field/travel': 'Terrain/Voyage',
        'Finance': 'Finance',
        'Health': 'Santé',
        'Education': 'Éducation',
        'Engineering': 'Ingénierie',
        'IT/Technology': 'IT/Technologie',
        'Sales/Marketing': 'Ventes/Marketing',
        'Research': 'Recherche',
        'Logistics': 'Logistique',
        'Procurement': 'Approvisionnement',
        'Monitoring & Evaluation': 'Suivi & Évaluation'
    }
   
    # Chercher une correspondance
    for eng, fr in translations.items():
        if eng.lower() in category.lower():
            return fr
   
    return category

def clean_location(location_text):
    """Nettoie le texte du lieu"""
    if not location_text:
        return ""
   
    # Diviser en lignes et garder seulement la première ligne significative
    lines = [line.strip() for line in location_text.split('\n') if line.strip()]
   
    for line in lines:
        # Chercher une ville ou un pays
        if (len(line) > 2 and len(line) < 50 and
            not any(word in line.lower() for word in ['full', 'time', 'part', 'contract', 'consultant']) and
            not any(word in line.lower() for word in ['management', 'development', 'finance', 'health']) and
            not line.isdigit()):
            return line
   
    # Si pas trouvé, prendre la première ligne
    return lines[0] if lines else ""

def real_scraping_clean():
    """Scraping avec nettoyage des données et extraction des URLs"""
    print("🌐 DÉMARRAGE DU SCRAPING...")
   
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('user-agent=Mozilla/5.0')
   
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://www.somalijobs.com/jobs")
        time.sleep(5)
       
        # Défilement
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
       
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
       
        # Chercher les offres
        job_containers = soup.find_all('a', class_='jobs-listing-container')
        print(f"📦 {len(job_containers)} offres trouvées")
       
        offres_propres = []
        base_url = "https://www.somalijobs.com"
       
        for container in job_containers:
            try:
                # URL de l'offre
                url = container.get('href', '')
                if url and not url.startswith('http'):
                    url = urljoin(base_url, url)
               
                # Titre (conservé en anglais pour référence)
                titre_elem = container.find('h2', class_='jobs-listing-title')
                titre_en = titre_elem.text.strip() if titre_elem else ""
                titre_fr = titre_en  # On pourrait ajouter des traductions spécifiques ici
               
                # Entreprise (conservée en anglais)
                entreprise_elem = container.find('p', class_='jobs-listing-company')
                entreprise_en = entreprise_elem.text.strip() if entreprise_elem else ""
                entreprise_fr = entreprise_en
               
                # Tout le texte pour analyse
                full_text = container.get_text()
               
                # Chercher la date en anglais d'abord
                date_en = ""
                patterns = [r'Today', r'Yesterday', r'Dec,\s*\d+', r'Nov,\s*\d+', r'Jan,\s*\d+', r'\d+\s+days?\s+ago']
                for pattern in patterns:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        date_en = match.group(0)
                        break
               
                # Traduire la date
                date_fr = translate_date(date_en)
               
                # Chercher le LIEU PROPRE
                lieu_en = ""
                if date_en:
                    # Trouver la position de la date
                    date_pos = full_text.find(date_en)
                    if date_pos != -1:
                        # Prendre le texte après la date
                        after_date = full_text[date_pos + len(date_en):]
                        # Nettoyer
                        lieu_en = clean_location(after_date)
               
                lieu_fr = lieu_en  # Les noms de lieux restent en anglais
               
                # Type de contrat
                type_contrat_en = ""
                types_en = ['Full Time', 'Part Time', 'Contract', 'Consultant', 'Temporary', 'Permanent', 'Internship']
                for t in types_en:
                    if t in full_text:
                        type_contrat_en = t
                        break
               
                type_contrat_fr = translate_contract_type(type_contrat_en)
               
                # Catégorie
                categorie_en = ""
                if type_contrat_en:
                    type_pos = full_text.find(type_contrat_en)
                    if type_pos != -1:
                        after_type = full_text[type_pos + len(type_contrat_en):]
                        # Nettoyer et prendre premier mot significatif
                        lines = [l.strip() for l in after_type.split('\n') if l.strip()]
                        for line in lines:
                            if line and len(line) > 2 and not line.isdigit():
                                categorie_en = line
                                break
               
                categorie_fr = translate_category(categorie_en)
               
                if titre_en:
                    offres_propres.append({
                        # Français
                        'titre_fr': titre_fr,
                        'entreprise_fr': entreprise_fr,
                        'date_fr': date_fr,
                        'lieu_fr': lieu_fr,
                        'type_contrat_fr': type_contrat_fr,
                        'categorie_fr': categorie_fr,
                       
                        # Anglais (original)
                        'titre_en': titre_en,
                        'entreprise_en': entreprise_en,
                        'date_en': date_en,
                        'lieu_en': lieu_en,
                        'type_contrat_en': type_contrat_en,
                        'categorie_en': categorie_en,
                       
                        'url': url
                    })
                   
            except Exception as e:
                print(f"⚠️ Erreur sur une offre: {e}")
                continue
       
        driver.quit()
        return offres_propres
       
    except Exception as e:
        print(f"❌ Erreur globale: {e}")
        if 'driver' in locals():
            driver.quit()
        return []

# ========== FORMAT FINAL PROPRE ==========
def get_final_output_french(offre):
    """Retourne le format final en français"""
    return f"""titre = recrutement d'un {offre['titre_fr']}
description = recrutement d'un {offre['titre_fr']}..
entreprise = {offre['entreprise_fr']} prometteur
lieu = {offre['lieu_fr'] or 'Non spécifié'}
pays = Somalie
avis = avis de candidature
source = somalijobs
type = national
nature = public
Type du Source de financement = national
caution = 0
secteur = Autres études, expertises et concours
url = {offre['url'] or 'Non disponible'}"""

# ========== AFFICHAGE BILINGUE ==========
def display_bilingual(offre, idx):
    """Affiche une offre en version bilingue"""
    print(f"\n📍 OFFRE {idx}:")
    print(f"   🇫🇷 Titre: {offre['titre_fr'][:60]}...")
    print(f"   🇬🇧 Title: {offre['titre_en'][:60]}...")
    print(f"   🇫🇷 Entreprise: {offre['entreprise_fr']}")
    print(f"   🇬🇧 Company: {offre['entreprise_en']}")
    print(f"   📅 Date: {offre['date_fr']}")
    if offre['date_en'] != offre['date_fr']:
        print(f"   📅 Date (EN): {offre['date_en']}")
    print(f"   📍 Lieu: {offre['lieu_fr'] or 'Non spécifié'}")
    print(f"   📍 Location: {offre['lieu_en'] or 'Not specified'}")
    print(f"   📋 Type: {offre['type_contrat_fr'] or 'N/A'}")
    if offre['type_contrat_en'] != offre['type_contrat_fr']:
        print(f"   📋 Type (EN): {offre['type_contrat_en'] or 'N/A'}")
    print(f"   🏷️ Catégorie: {offre['categorie_fr'] or 'N/A'}")
    if offre['categorie_en'] != offre['categorie_fr']:
        print(f"   🏷️ Category: {offre['categorie_en'] or 'N/A'}")
    print(f"   🔗 URL: {offre['url'][:80]}..." if offre['url'] else "   🔗 URL: Non disponible")
    print("-" * 80)

# ========== EXPORT EN CSV ==========
def export_to_csv(offres, filename="offres_somalijobs.csv"):
    """Exporte les offres en fichier CSV"""
    import csv
   
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'titre_fr', 'titre_en',
            'entreprise_fr', 'entreprise_en',
            'date_fr', 'date_en',
            'lieu_fr', 'lieu_en',
            'type_contrat_fr', 'type_contrat_en',
            'categorie_fr', 'categorie_en',
            'url'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
       
        writer.writeheader()
        for offre in offres:
            writer.writerow({
                'titre_fr': offre['titre_fr'],
                'titre_en': offre['titre_en'],
                'entreprise_fr': offre['entreprise_fr'],
                'entreprise_en': offre['entreprise_en'],
                'date_fr': offre['date_fr'],
                'date_en': offre['date_en'],
                'lieu_fr': offre['lieu_fr'],
                'lieu_en': offre['lieu_en'],
                'type_contrat_fr': offre['type_contrat_fr'],
                'type_contrat_en': offre['type_contrat_en'],
                'categorie_fr': offre['categorie_fr'],
                'categorie_en': offre['categorie_en'],
                'url': offre['url']
            })
   
    print(f"✅ Données exportées dans {filename}")

# ========== PROGRAMME PRINCIPAL ==========
print("="*100)
print("🚀 SCRAPING - SOMALIJOBS.COM (Version bilingue)")
print("="*100)

# Lancer le scraping
offres = real_scraping_clean()

if not offres:
    print("❌ Aucune donnée récupérée")
    exit()

# Statistiques rapides
print(f"\n📊 {len(offres)} offres récupérées avec succès!")

# Menu dates
print("\n" + "="*100)
print("📅 FILTRER PAR DATE")
print("="*100)

# Grouper par date (en français)
date_groups = {}
for o in offres:
    date = o['date_fr'] or 'Date inconnue'
    if date not in date_groups:
        date_groups[date] = []
    date_groups[date].append(o)

# Trier
sorted_dates = []
for pref in ["Aujourd'hui", "Hier"]:
    if pref in date_groups:
        sorted_dates.append(pref)

other_dates = sorted([d for d in date_groups.keys() if d not in ["Aujourd'hui", "Hier", 'Date inconnue']])
sorted_dates.extend(other_dates)

if 'Date inconnue' in date_groups:
    sorted_dates.append('Date inconnue')

# Afficher menu
for i, date in enumerate(sorted_dates, 1):
    count = len(date_groups[date])
    print(f"{i}. {date} ({count} offres)")

print(f"{len(sorted_dates)+1}. TOUTES")
print(f"{len(sorted_dates)+2}. AFFICHER BILINGUE (10 premières)")
print(f"{len(sorted_dates)+3}. EXPORTER TOUT EN CSV")
print(f"{len(sorted_dates)+4}. QUITTER")

choix = input("\n👉 Choisis: ").strip()

if choix == str(len(sorted_dates)+4):
    print("👋 Au revoir!")
    exit()
elif choix == str(len(sorted_dates)+3):
    export_to_csv(offres)
    print("✅ Export CSV terminé!")
    exit()
elif choix == str(len(sorted_dates)+2):
    # Affichage bilingue des 10 premières offres
    print("\n" + "="*100)
    print("📄 AFFICHAGE BILINGUE - 10 PREMIÈRES OFFRES")
    print("="*100)
    for idx, offre in enumerate(offres[:10], 1):
        display_bilingual(offre, idx)
   
    # Option pour voir plus
    if len(offres) > 10:
        voir_plus = input(f"\n📋 Voir les {len(offres)-10} offres restantes ? (o/n): ").strip().lower()
        if voir_plus == 'o':
            for idx, offre in enumerate(offres[10:], 11):
                display_bilingual(offre, idx)
   
    export_opt = input("\n📤 Exporter toutes les données en CSV ? (o/n): ").strip().lower()
    if export_opt == 'o':
        export_to_csv(offres)
    exit()

# Filtrer
if choix == str(len(sorted_dates)+1):
    offres_filtrees = offres
    date_selectionnee = "TOUTES"
elif choix.isdigit() and 1 <= int(choix) <= len(sorted_dates):
    date_selectionnee = sorted_dates[int(choix)-1]
    offres_filtrees = date_groups[date_selectionnee]
else:
    offres_filtrees = offres
    date_selectionnee = "TOUTES"

# OUTPUT FINAL EN FRANÇAIS
print("\n" + "="*100)
print(f"✅ EXTRACTION - {date_selectionnee}")
print("="*100)
print(f"📊 {len(offres_filtrees)} OFFRES")
print("="*100)

for idx, offre in enumerate(offres_filtrees, 1):
    print(f"\n📍 OFFRE {idx}:")
    print(get_final_output_french(offre))
    print("-" * 100)

# Option d'export final
print(f"\n🎯 {len(offres_filtrees)} offres extraites et formatées !")
print("\n📤 OPTIONS D'EXPORT:")
print("1. Exporter en CSV (version bilingue)")
print("2. Exporter en CSV (version française uniquement)")
print("3. Afficher version bilingue")
print("4. Quitter")

export_choix = input("\n👉 Choisis: ").strip()

if export_choix == '1':
    if date_selectionnee == "TOUTES":
        filename = "offres_toutes_bilingues.csv"
    else:
        filename = f"offres_{date_selectionnee.lower().replace(' ', '_').replace(',', '')}_bilingue.csv"
    export_to_csv(offres_filtrees, filename)
    print("✅ Export CSV bilingue terminé!")
elif export_choix == '2':
    # Export version française uniquement
    import csv
    if date_selectionnee == "TOUTES":
        filename = "offres_toutes_francais.csv"
    else:
        filename = f"offres_{date_selectionnee.lower().replace(' ', '_').replace(',', '')}_francais.csv"
   
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['titre', 'entreprise', 'date', 'lieu', 'type_contrat', 'categorie', 'url']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
       
        writer.writeheader()
        for offre in offres_filtrees:
            writer.writerow({
                'titre': offre['titre_fr'],
                'entreprise': offre['entreprise_fr'],
                'date': offre['date_fr'],
                'lieu': offre['lieu_fr'],
                'type_contrat': offre['type_contrat_fr'],
                'categorie': offre['categorie_fr'],
                'url': offre['url']
            })
   
    print(f"✅ Export CSV français terminé dans {filename}!")
elif export_choix == '3':
    print("\n" + "="*100)
    print("📄 AFFICHAGE BILINGUE COMPLET")
    print("="*100)
    for idx, offre in enumerate(offres_filtrees, 1):
        display_bilingual(offre, idx)

print("="*100)