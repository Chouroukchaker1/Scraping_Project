import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import os
import sys
from datetime import datetime, timedelta
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException

class NigerEmploiScraper:
    def __init__(self, take_screenshots=True):
        self.base_url = "https://www.nigeremploi.com/"
        self.annonces_url = "https://www.nigeremploi.com/emplois-annonces.html"
        self.tenders_data = []
        self.session = requests.Session()
        self.take_screenshots = take_screenshots
        self.screenshot_dir = "nigerscreenshots"
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        })
       
        # Créer le dossier pour les screenshots
        os.makedirs(self.screenshot_dir, exist_ok=True)
        print(f"✅ Dossier créé: {self.screenshot_dir}")
       
        # Initialiser Selenium pour les captures d'écran (si activé)
        self.driver = None
        if self.take_screenshots:
            self.init_selenium()
   
    def init_selenium(self):
        """Initialise Selenium pour les captures d'écran avec différentes méthodes"""
        print("🔄 Initialisation de Selenium pour les captures d'écran...")
       
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")  # Nouveau mode headless
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--start-maximized")
           
            # Options pour accélérer le chargement
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
           
            # Désactiver les images pour accélérer
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2
            }
            chrome_options.add_experimental_option("prefs", prefs)
           
            # Méthode 1: Essayer avec le chemin direct de Chrome
            chrome_paths = [
                # Windows
                "C:/Program Files/Google/Chrome/Application/chrome.exe",
                "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
                # Linux
                "/usr/bin/google-chrome",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                # Mac
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            ]
           
            for chrome_path in chrome_paths:
                if os.path.exists(chrome_path):
                    chrome_options.binary_location = chrome_path
                    print(f"✅ Chrome trouvé à: {chrome_path}")
                    break
           
            # Essayer plusieurs méthodes pour le driver
            try:
                # Méthode 1: Driver système
                self.driver = webdriver.Chrome(options=chrome_options)
                print("✅ Selenium initialisé avec Chrome système")
            except:
                try:
                    # Méthode 2: Avec chromedriver-autoinstaller
                    import chromedriver_autoinstaller
                    chromedriver_autoinstaller.install()
                    self.driver = webdriver.Chrome(options=chrome_options)
                    print("✅ Selenium initialisé avec chromedriver-autoinstaller")
                except:
                    # Méthode 3: Chemin manuel
                    if sys.platform == "win32":
                        driver_path = "chromedriver.exe"
                    else:
                        driver_path = "chromedriver"
                   
                    service = Service(driver_path)
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    print("✅ Selenium initialisé avec driver manuel")
           
            # Configurer le timeout
            self.driver.set_page_load_timeout(30)
            print("✅ Selenium prêt pour les captures d'écran")
           
        except Exception as e:
            print(f"❌ ERREUR Selenium: {e}")
            print("\n🔧 SOLUTIONS POSSIBLES:")
            print("1. Installez Chrome: https://www.google.com/chrome/")
            print("2. Ou téléchargez chromedriver: https://chromedriver.chromium.org/")
            print("3. Placez chromedriver dans le même dossier que ce script")
            print("4. Désactivez les captures avec l'option 2")
            print("\n⚠️  Les captures d'écran seront désactivées")
            self.take_screenshots = False
   
    def get_date_choice(self):
        """Interface de sélection de date avec plage"""
        print("=" * 60)
        print("📅 SÉLECTEUR DE DATE")
        print("=" * 60)
        print("Options:")
        print("1. Toutes les dates")
        print("2. Derniers 7 jours")
        print("3. Derniers 30 jours")
        print("4. Plage de dates personnalisée (de ... à ...)")
        print("5. Aujourd'hui seulement")
        print("=" * 60)
       
        try:
            choice = int(input("Votre choix (1-5): "))
            if choice not in [1, 2, 3, 4, 5]:
                raise ValueError
           
            if choice == 4:  # Plage de dates
                print("\n🔸 Entrez la date de DÉBUT (format: JJ/MM/AAAA)")
                date_debut = input("Date début: ")
                print("🔸 Entrez la date de FIN (format: JJ/MM/AAAA)")
                date_fin = input("Date fin: ")
                return choice, (date_debut, date_fin)
            else:
                return choice, None
               
        except:
            print("❌ Choix invalide, utilisation de toutes les dates")
            return 1, None
   
    def parse_date(self, date_str):
        """Parse une date avec différents formats"""
        if not date_str:
            return None
           
        date_str = date_str.strip()
       
        # Essayer différents formats
        date_formats = ['%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y', '%Y-%m-%d']
       
        for date_format in date_formats:
            try:
                return datetime.strptime(date_str, date_format)
            except:
                continue
       
        return None
   
    def filter_by_date_range(self, date_str, choice, date_range=None):
        """Filtre les annonces par plage de dates"""
        if choice == 1:  # Toutes les dates
            return True
       
        # Parser la date de l'annonce
        annonce_date = self.parse_date(date_str)
        if not annonce_date:
            return True  # Si on ne peut pas parser, on garde
       
        if choice == 2:  # 7 derniers jours
            cutoff_date = datetime.now() - timedelta(days=7)
            return annonce_date >= cutoff_date
           
        elif choice == 3:  # 30 derniers jours
            cutoff_date = datetime.now() - timedelta(days=30)
            return annonce_date >= cutoff_date
           
        elif choice == 4:  # Plage de dates personnalisée
            if date_range and len(date_range) == 2:
                date_debut_str, date_fin_str = date_range
               
                date_debut = self.parse_date(date_debut_str)
                date_fin = self.parse_date(date_fin_str)
               
                if date_debut and date_fin:
                    # Ajouter un jour à la date de fin pour inclure toute la journée
                    date_fin = date_fin + timedelta(days=1)
                    return date_debut <= annonce_date <= date_fin
           
            return True
           
        elif choice == 5:  # Aujourd'hui
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            return today <= annonce_date < tomorrow
       
        return True
   
    def take_screenshot(self, url, reference, titre):
        """Prend une capture d'écran de la page d'annonce"""
        if not self.take_screenshots or not self.driver:
            return None
       
        try:
            print(f"   📸 Capture pour: {reference}")
            print(f"   📄 {titre[:60]}...")
           
            # Accéder à la page
            self.driver.get(url)
            time.sleep(3)  # Attendre le chargement
           
            # Définir la taille pour capturer toute la page
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            viewport_height = self.driver.execute_script("return window.innerHeight")
           
            # Si la page est longue, ajuster la taille
            if total_height > 2000:
                self.driver.set_window_size(1920, min(total_height, 5000))
           
            # Prendre la capture d'écran
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{reference}_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
           
            self.driver.save_screenshot(filepath)
           
            # Vérifier la capture
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath) / 1024  # Taille en KB
                if file_size > 10:  # Au moins 10KB
                    print(f"   ✅ Capture réussie: {filename} ({file_size:.1f} KB)")
                    return filepath
                else:
                    print(f"   ⚠️ Capture trop petite: {file_size:.1f} KB")
                    return None
            else:
                print(f"   ❌ Capture échouée")
                return None
               
        except Exception as e:
            print(f"   ❌ Erreur capture: {str(e)[:50]}...")
            return None
   
    def extract_annonce_data(self, annonce_div):
        """Extrait les données d'une annonce depuis le HTML"""
        try:
            # 1. TITRE et LIEN
            titre_tag = annonce_div.find('span', class_='txt_fs11_c')
            titre = titre_tag.get_text(strip=True) if titre_tag else "Non spécifié"
           
            lien_tag = annonce_div.find('a', href=True)
            lien = lien_tag['href'] if lien_tag else ""
            if lien and not lien.startswith('http'):
                lien = self.base_url.rstrip('/') + '/' + lien.lstrip('/')
           
            # 2. RÉFÉRENCE (depuis le lien ou générée)
            reference = "NE-N/A"
            if lien:
                match = re.search(r'annonce-details-(\d+)', lien)
                if match:
                    reference = f"NE-{match.group(1)}"
           
            # 3. PROMOTEUR/RECRUTEUR
            promoteur = "Non spécifié"
            promoteur_tag = annonce_div.find('a', class_='ss_miz_f', href=re.compile(r'recherche_offre-structure-'))
            if promoteur_tag:
                promoteur = promoteur_tag.get('title', '').replace('Recruteur: ', '')
                if not promoteur or promoteur == 'Recruteur: ':
                    promoteur = promoteur_tag.get_text(strip=True)
           
            # 4. DATES
            date_publication = ""
            date_expiration = ""
           
            all_text = annonce_div.get_text()
            date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
            dates = re.findall(date_pattern, all_text)
           
            if len(dates) >= 1:
                date_publication = dates[0]
            if len(dates) >= 2:
                date_expiration = dates[1]
           
            # Recherche avec icônes
            date_tags = annonce_div.find_all('i', class_=re.compile(r'fa-calendar'))
            for date_tag in date_tags:
                parent_text = date_tag.parent.get_text()
                date_match = re.search(date_pattern, parent_text)
                if date_match:
                    if 'calendar-times-o' in date_tag.get('class', []):
                        date_expiration = date_match.group(1)
                    else:
                        date_publication = date_match.group(1)
           
            # 5. TYPE D'ANNONCE
            type_annonce = "annonce"
            type_tag = annonce_div.find('a', class_='ss_miz_f', href=re.compile(r'recherche_offre-categorie-'))
            if type_tag:
                type_text = type_tag.get_text(strip=True).lower()
                if 'appel' in type_text or 'ao' in type_text:
                    type_annonce = "Appel d'offre"
                elif 'formation' in type_text:
                    type_annonce = "Formation"
                elif 'concours' in type_text:
                    type_annonce = "Concours"
                elif 'consultation' in type_text:
                    type_annonce = "Consultation"
                else:
                    type_annonce = type_text
           
            # 6. TYPE DE FINANCEMENT (TOUJOURS "national")
            type_financement = "national"
           
            # 7. NATURE (toujours public)
            nature = "public"
           
            # 8. TYPE (toujours national)
            type_value = "national"
           
            # 9. PAYS (toujours Niger)
            pays = "niger"
           
            # 10. CAUTION (toujours 0)
            caution = "0"
           
            # 11. RETRAIT DE CAHIER DE CHARGE
            retrait_cahier_charge = lien
           
            # 12. DESCRIPTION
            description = titre
           
            # Créer l'objet annonce
            annonce_data = {
                'reference': reference,
                'titre': titre,
                'description': description,
                'promoteur': promoteur,
                'date_publication': date_publication,
                'date_expiration': date_expiration,
                'retrait_cahier_charge': retrait_cahier_charge,
                'type_financement': type_financement,
                'nature': nature,
                'type': type_value,
                'pays': pays,
                'caution': caution,
                'photo': None  # Sera rempli avec le chemin du screenshot
            }
           
            return annonce_data
           
        except Exception as e:
            print(f"⚠️ Erreur extraction: {e}")
            return None
   
    def process_annonce_with_screenshot(self, annonce_data):
        """Traite une annonce et prend une capture d'écran"""
        if annonce_data and annonce_data.get('retrait_cahier_charge'):
            screenshot_path = self.take_screenshot(
                annonce_data['retrait_cahier_charge'],
                annonce_data['reference'],
                annonce_data['titre']
            )
           
            if screenshot_path:
                annonce_data['photo'] = screenshot_path
           
            # Pause pour ne pas surcharger
            time.sleep(2)
       
        return annonce_data
   
    def scrape_page(self, url, date_choice=1, date_range=None):
        """Scrape une page spécifique"""
        try:
            response = self.session.get(url, timeout=30)
           
            if response.status_code != 200:
                return [], 0
           
            soup = BeautifulSoup(response.content, 'html.parser')
            annonces_divs = soup.find_all('div', class_='div_rz_ance_gnral')
           
            page_annonces = []
            for annonce_div in annonces_divs:
                annonce_data = self.extract_annonce_data(annonce_div)
                if annonce_data and annonce_data.get('reference'):
                    if annonce_data['reference'] != "NE-N/A":
                        if annonce_data['date_publication']:
                            if self.filter_by_date_range(annonce_data['date_publication'], date_choice, date_range):
                                page_annonces.append(annonce_data)
                        else:
                            page_annonces.append(annonce_data)
           
            return page_annonces, len(annonces_divs)
           
        except Exception as e:
            print(f"❌ Erreur scraping {url}: {e}")
            return [], 0
   
    def scrape_all_pages(self, date_choice=1, date_range=None):
        """Scrape toutes les pages"""
        print("=" * 60)
        print("🔄 EXTRACTION DES DONNÉES")
        print("=" * 60)
       
        if date_choice == 4 and date_range:
            print(f"📅 Filtrage: du {date_range[0]} au {date_range[1]}")
       
        print("🔍 Récupération des annonces...")
       
        all_annonces = []
       
        # Page d'accueil
        print("📄 Récupération page 1 (accueil)...")
        page_annonces, count = self.scrape_page(self.base_url, date_choice, date_range)
       
        if page_annonces:
            all_annonces.extend(page_annonces)
            print(f"✅ Page 1: {len(page_annonces)} annonces")
       
        # Page toutes les annonces
        print("📄 Récupération page toutes les annonces...")
        page_annonces, count = self.scrape_page(self.annonces_url, date_choice, date_range)
       
        if page_annonces:
            all_annonces.extend(page_annonces)
            print(f"✅ Page annonces: {len(page_annonces)} annonces")
       
        # Supprimer les doublons
        unique_annonces = []
        seen_references = set()
       
        for annonce in all_annonces:
            if annonce['reference'] not in seen_references:
                seen_references.add(annonce['reference'])
                unique_annonces.append(annonce)
       
        print(f"\n✅ {len(unique_annonces)} annonces récupérées au total")
       
        # Prendre les captures d'écran si activé
        if self.take_screenshots and unique_annonces and self.driver:
            print("\n" + "=" * 60)
            print("📸 CAPTURES D'ÉCRAN EN COURS")
            print("=" * 60)
            print(f"📁 Dossier: {self.screenshot_dir}")
            print(f"📊 Nombre d'annonces: {len(unique_annonces)}")
            print("⏱️  Temps estimé: ~{:.0f} secondes".format(len(unique_annonces) * 5))
            print("=" * 60)
           
            processed_annonces = []
            for i, annonce in enumerate(unique_annonces, 1):
                print(f"\n[{i}/{len(unique_annonces)}] ", end="")
                processed_annonce = self.process_annonce_with_screenshot(annonce)
                if processed_annonce:
                    processed_annonces.append(processed_annonce)
           
            print("\n" + "=" * 60)
            print("✅ CAPTURES D'ÉCRAN TERMINÉES")
            print("=" * 60)
           
            return processed_annonces
       
        return unique_annonces
   
    def display_results(self, annonces):
        """Affiche les résultats"""
        print("=" * 60)
        print("👁️  AFFICHAGE DES RÉSULTATS")
        print("=" * 60)
        print("\n" + "=" * 120)
        print("📋 LISTE DES APPELS D'OFFRES - NIGEREMPLOI")
        print("=" * 120 + "\n")
       
        if not annonces:
            print("❌ Aucune annonce à afficher")
            return
       
        for annonce in annonces:
            print(f"📌 Référence: {annonce['reference']}")
            print(f"   titre : {annonce['titre']}")
            print(f"   description : {annonce['description']}")
            print(f"   🏛️  promoteur : {annonce['promoteur']}")
            print(f"   📅 date de Publication: {annonce['date_publication']}")
            print(f"   ⏰ date d'expiration : {annonce['date_expiration']}")
            print(f"   📄 Retrait de cahier de charge: {annonce['retrait_cahier_charge']}")
           
            if annonce.get('photo'):
                print(f"   📸 photo: {annonce['photo']}")
           
            print(f"   type de financement : {annonce['type_financement']}")
            print(f"   nature : {annonce['nature']}")
            print(f"   type : {annonce['type']}")
            print(f"   pays : {annonce['pays']}")
            print(f"   caution : {annonce['caution']}")
            print("   " + "─" * 116)
            print()
       
        print(f"📊 Total: {len(annonces)} annonces")
       
        # Statistiques des captures
        if self.take_screenshots:
            screenshots_count = sum(1 for a in annonces if a.get('photo'))
            print(f"\n📸 Captures réussies: {screenshots_count}/{len(annonces)}")
   
    def save_data(self, annonces):
        """Sauvegarde les données"""
        print("=" * 60)
        print("💾 SAUVEGARDE AUTOMATIQUE")
        print("=" * 60)
       
        if not annonces:
            print("⚠️ Aucune donnée à sauvegarder")
            return
       
        # Créer DataFrame
        df = pd.DataFrame(annonces)
       
        columns_order = [
            'reference', 'titre', 'description', 'promoteur', 'date_publication',
            'date_expiration', 'retrait_cahier_charge', 'photo', 'type_financement',
            'nature', 'type', 'pays', 'caution'
        ]
       
        columns_order = [col for col in columns_order if col in df.columns]
        df = df[columns_order]
       
        # Timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
       
        # JSON
        json_filename = f"nigeremploi_annonces_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(annonces, f, ensure_ascii=False, indent=2)
        print(f"💾 JSON: {json_filename}")
       
        # CSV
        csv_filename = f"nigeremploi_annonces_{timestamp}.csv"
        df.to_csv(csv_filename, index=False, encoding='utf-8')
        print(f"📄 CSV: {csv_filename}")
       
        # Excel
        excel_filename = f"nigeremploi_annonces_{timestamp}.xlsx"
        df.to_excel(excel_filename, index=False)
        print(f"📊 Excel: {excel_filename}")
       
        # Résumé captures
        if self.take_screenshots:
            screenshots = [a for a in annonces if a.get('photo')]
            if screenshots:
                total_size = sum(os.path.getsize(a['photo']) for a in screenshots if a['photo'] and os.path.exists(a['photo']))
                avg_size = total_size / len(screenshots) / 1024 if screenshots else 0
               
                print(f"\n📸 CAPTURES D'ÉCRAN:")
                print(f"   📁 Dossier: {self.screenshot_dir}/")
                print(f"   ✅ Captures réussies: {len(screenshots)}/{len(annonces)}")
                print(f"   📏 Taille moyenne: {avg_size:.1f} KB")
                print(f"   💾 Taille totale: {total_size/1024/1024:.2f} MB")
       
        print("\n✅ Sauvegarde terminée !")
   
    def cleanup(self):
        """Nettoie les ressources"""
        if self.driver:
            self.driver.quit()
            print("✅ Driver Selenium fermé")
   
    def run_full_scraping(self, date_choice=1, date_range=None, auto_save=True):
        """Exécute le scraping complet avec les paramètres donnés"""
        print("=" * 60)
        print("🚀 DÉMARRAGE DU SCRAPING AVEC CAPTURES D'ÉCRAN")
        print("=" * 60)
       
        try:
            # Extraction
            all_annonces = self.scrape_all_pages(date_choice, date_range)
           
            # Affichage
            self.display_results(all_annonces)
           
            # Sauvegarde automatique
            if auto_save and all_annonces:
                print("\n" + "=" * 60)
                print("💾 SAUVEGARDE AUTOMATIQUE EN COURS...")
                print("=" * 60)
                self.save_data(all_annonces)
            elif not all_annonces:
                print("\n⚠️  Aucune donnée à sauvegarder")
           
            print("\n" + "=" * 60)
            print("✅ SCRAPING TERMINÉ AVEC SUCCÈS !")
            print("=" * 60)
           
            return all_annonces
           
        except Exception as e:
            print(f"\n\n❌ Erreur: {e}")
            return []
        finally:
            self.cleanup()

# Fonction principale simplifiée pour lancer directement avec captures
def main():
    """Fonction principale qui lance directement le scraping avec captures"""
   
    # Installer les dépendances automatiquement
    def install_dependencies():
        """Installe les dépendances manquantes"""
        import subprocess
        import importlib
       
        required = ['selenium', 'pandas', 'beautifulsoup4', 'requests', 'openpyxl']
       
        for package in required:
            try:
                importlib.import_module(package.split('==')[0])
                print(f"✅ {package} déjà installé")
            except ImportError:
                print(f"📦 Installation de {package}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"✅ {package} installé")
   
    # Installer les dépendances
    print("=" * 60)
    print("🛠️  INSTALLATION & CONFIGURATION")
    print("=" * 60)
    install_dependencies()
   
    print("\n" + "=" * 60)
    print("📋 PROGRAMME DE SCRAPING NIGEREMPLOI")
    print("=" * 60)
   
    # Étape 1: Sélection de la date
    print("\n📅 SÉLECTEUR DE DATE")
    print("=" * 60)
    print("Options:")
    print("1. Toutes les dates")
    print("2. Derniers 7 jours")
    print("3. Derniers 30 jours")
    print("4. Plage de dates personnalisée (de ... à ...)")
    print("5. Aujourd'hui seulement")
    print("=" * 60)
   
    try:
        choice = int(input("Votre choix (1-5): "))
        if choice not in [1, 2, 3, 4, 5]:
            raise ValueError
       
        date_range = None
        if choice == 4:  # Plage de dates
            print("\n🔸 Entrez la date de DÉBUT (format: JJ/MM/AAAA)")
            date_debut = input("Date début: ")
            print("🔸 Entrez la date de FIN (format: JJ/MM/AAAA)")
            date_fin = input("Date fin: ")
            date_range = (date_debut, date_fin)
           
    except:
        print("❌ Choix invalide, utilisation de toutes les dates")
        choice = 1
        date_range = None
   
    # Étape 2: Lancer directement le scraping avec captures
    print("\n" + "=" * 60)
    print("🚀 LANCEMENT AUTOMATIQUE AVEC CAPTURES")
    print("=" * 60)
    print("📸 Mode: Avec captures d'écran")
    print(f"📁 Dossier des captures: nigerscreenshots/")
    print("⏱️  Temps estimé: ~30 secondes par annonce")
    print("=" * 60)
   
    # Créer et lancer le scraper avec captures
    scraper = NigerEmploiScraper(take_screenshots=True)
   
    # Lancer le scraping complet
    annonces = scraper.run_full_scraping(
        date_choice=choice,
        date_range=date_range,
        auto_save=True  # Sauvegarde automatique activée
    )
   
    print("\n" + "=" * 60)
    print("🎯 SCRAPING COMPLÈTEMENT TERMINÉ")
    print("=" * 60)
   
    if annonces:
        print(f"📊 {len(annonces)} annonces traitées avec succès")
        print("💾 Données sauvegardées dans les fichiers:")
        print("   - JSON (.json)")
        print("   - CSV (.csv)")
        print("   - Excel (.xlsx)")
        print(f"📸 Captures dans: nigerscreenshots/")
    else:
        print("⚠️  Aucune annonce trouvée avec les critères sélectionnés")

# Script d'installation (pour exécution directe)
if __name__ == "__main__":
    # Cette partie ne sera exécutée que si le script est lancé directement
    # et non importé comme module
    main()