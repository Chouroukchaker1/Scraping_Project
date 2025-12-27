# Installation des dépendances pour Google Colab
import sys
sys.path.insert(0,'/usr/lib/chromium-browser/chromedriver')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import pandas as pd
import json
import time
from datetime import datetime

class AppelOffresSeleniumScraper:
    def __init__(self):
        """Initialise le scraper avec Selenium"""
        print("🔧 Initialisation de Selenium...")
        
        # Configuration Chrome pour Google Colab
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Utiliser chromium-browser de Colab
        chrome_options.binary_location = '/usr/bin/chromium-browser'
        
        # Initialiser le driver avec chromedriver de Colab
        service = Service('/usr/bin/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Masquer l'automation
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.wait = WebDriverWait(self.driver, 20)
        
        self.base_url = 'https://bo.appeloffres.net'
        self.login_url = f'{self.base_url}/auth/login/'
        self.subscriptions_url = f'{self.base_url}/dashboard/subscriptions/'
        
        print("   ✅ Selenium initialisé avec Chromium")
    
    def login(self, email, password):
        """Connexion avec Selenium"""
        print("\n🔐 Connexion avec Selenium...")
        
        try:
            # Charger la page de login
            print("   📄 Chargement de la page de login...")
            self.driver.get(self.login_url)
            time.sleep(3)
            
            print(f"   URL actuelle: {self.driver.current_url}")
            print(f"   Titre: {self.driver.title}")
            
            # Chercher les champs de login
            print("\n   🔍 Recherche des champs de formulaire...")
            
            # Méthode 1: Par type
            try:
                email_input = self.driver.find_element(By.CSS_SELECTOR, 'input[type="email"], input[name*="email"], input[id*="email"]')
                password_input = self.driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
                print("   ✅ Champs trouvés par CSS selector")
            except:
                # Méthode 2: Par name
                try:
                    email_input = self.driver.find_element(By.NAME, 'email')
                    password_input = self.driver.find_element(By.NAME, 'password')
                    print("   ✅ Champs trouvés par name")
                except:
                    # Méthode 3: Par placeholder
                    email_input = self.driver.find_element(By.XPATH, '//input[@placeholder="Email" or @placeholder="E-mail"]')
                    password_input = self.driver.find_element(By.XPATH, '//input[@placeholder="Password" or @placeholder="Mot de passe"]')
                    print("   ✅ Champs trouvés par placeholder")
            
            # Remplir les champs
            print("   ✏️ Remplissage des champs...")
            email_input.clear()
            email_input.send_keys(email)
            time.sleep(0.5)
            
            password_input.clear()
            password_input.send_keys(password)
            time.sleep(0.5)
            
            # Chercher et cliquer sur le bouton de connexion
            print("   🖱️ Clic sur le bouton de connexion...")
            
            try:
                # Méthode 1: Par type submit
                submit_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"]')
            except:
                # Méthode 2: Par texte
                submit_button = self.driver.find_element(By.XPATH, '//button[contains(text(), "Connexion") or contains(text(), "Login") or contains(text(), "Se connecter")]')
            
            submit_button.click()
            
            # Attendre la redirection
            print("   ⏳ Attente de la redirection...")
            time.sleep(5)
            
            print(f"   URL après login: {self.driver.current_url}")
            
            # Vérifier si connecté
            if 'dashboard' in self.driver.current_url or 'login' not in self.driver.current_url:
                print("   ✅ Connexion réussie!")
                return True
            else:
                print("   ❌ Échec de la connexion")
                # Sauvegarder screenshot pour debug
                self.driver.save_screenshot('login_error.png')
                print("   💾 Screenshot sauvegardé: login_error.png")
                return False
                
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            self.driver.save_screenshot('login_error.png')
            return False
    
    def navigate_to_subscriptions(self):
        """Navigation vers la page des abonnements"""
        print("\n📍 Navigation vers les abonnements...")
        
        try:
            self.driver.get(self.subscriptions_url)
            print(f"   URL: {self.driver.current_url}")
            
            # Attendre que la page charge
            time.sleep(5)
            
            print("   ✅ Page chargée")
            return True
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return False
    
    def wait_for_data_to_load(self):
        """Attendre que les données se chargent"""
        print("\n⏳ Attente du chargement des données...")
        
        max_wait = 30  # 30 secondes max
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            # Vérifier plusieurs indicateurs de chargement
            try:
                # 1. Recherche de tables
                tables = self.driver.find_elements(By.TAG_NAME, 'table')
                if tables:
                    print(f"   ✅ Table trouvée ({len(tables)} table(s))")
                    return True
                
                # 2. Recherche de divs avec role="row"
                rows = self.driver.find_elements(By.CSS_SELECTOR, '[role="row"], .table-row, .data-row')
                if len(rows) > 1:  # Plus que le header
                    print(f"   ✅ Lignes de données trouvées ({len(rows)} ligne(s))")
                    return True
                
                # 3. Vérifier si le loading a disparu
                loaders = self.driver.find_elements(By.CSS_SELECTOR, '.loading, .spinner, [role="progressbar"]')
                if not loaders:
                    time.sleep(2)  # Attendre un peu plus
                    # Re-vérifier
                    tables = self.driver.find_elements(By.TAG_NAME, 'table')
                    rows = self.driver.find_elements(By.CSS_SELECTOR, '[role="row"], .table-row, .data-row')
                    if tables or len(rows) > 1:
                        print(f"   ✅ Données chargées")
                        return True
                
            except:
                pass
            
            time.sleep(1)
            print("   ⏳ En attente...")
        
        print("   ⚠️ Timeout - Extraction quand même...")
        return False
    
    def extract_subscriptions(self):
        """Extrait les données des abonnements"""
        print("\n🔍 Extraction des données...")
        
        subscriptions = []
        
        # Méthode 1: Extraire depuis JavaScript
        print("\n   📦 Méthode 1: Extraction via JavaScript...")
        try:
            # Essayer de récupérer les données depuis window, store Redux, etc.
            js_data_scripts = [
                "return window.__INITIAL_STATE__",
                "return window.__data",
                "return window.subscriptions",
                "return document.querySelector('[data-subscriptions]')?.dataset.subscriptions",
            ]
            
            for script in js_data_scripts:
                try:
                    result = self.driver.execute_script(script)
                    if result:
                        print(f"      ✅ Données trouvées via: {script}")
                        if isinstance(result, str):
                            result = json.loads(result)
                        if isinstance(result, list):
                            return result
                        elif isinstance(result, dict):
                            for key in ['subscriptions', 'data', 'items']:
                                if key in result:
                                    return result[key]
                except:
                    pass
        except Exception as e:
            print(f"      ⚠️ Erreur JavaScript: {e}")
        
        # Méthode 2: Parser le HTML avec Selenium
        print("\n   🔧 Méthode 2: Parsing HTML...")
        
        try:
            # Table HTML classique
            tables = self.driver.find_elements(By.TAG_NAME, 'table')
            if tables:
                print(f"      Tables trouvées: {len(tables)}")
                for table in tables:
                    rows = table.find_elements(By.TAG_NAME, 'tr')
                    print(f"      Lignes: {len(rows)}")
                    
                    for i, row in enumerate(rows[1:], 1):  # Skip header
                        cols = row.find_elements(By.TAG_NAME, 'td')
                        if len(cols) >= 7:
                            subscription = {
                                'ID': cols[0].text.strip() if len(cols) > 0 else '',
                                'ID_client': cols[1].text.strip() if len(cols) > 1 else '',
                                'Email': cols[2].text.strip() if len(cols) > 2 else '',
                                'Numero_contact': cols[3].text.strip() if len(cols) > 3 else '',
                                'Type_abonnement': cols[4].text.strip() if len(cols) > 4 else '',
                                'Date_debut': cols[5].text.strip() if len(cols) > 5 else '',
                                'Date_fin': cols[6].text.strip() if len(cols) > 6 else '',
                                'Status': cols[7].text.strip() if len(cols) > 7 else '',
                                'Date_creation': cols[8].text.strip() if len(cols) > 8 else ''
                            }
                            subscriptions.append(subscription)
                            
            if subscriptions:
                print(f"      ✅ {len(subscriptions)} abonnements extraits")
                return subscriptions
                
        except Exception as e:
            print(f"      ⚠️ Erreur: {e}")
        
        # Méthode 3: Divs avec role="row"
        print("\n   🔧 Méthode 3: Divs avec role='row'...")
        try:
            rows = self.driver.find_elements(By.CSS_SELECTOR, '[role="row"]')
            if not rows:
                rows = self.driver.find_elements(By.CSS_SELECTOR, '.table-row, .data-row, .grid-row')
            
            print(f"      Lignes trouvées: {len(rows)}")
            
            for i, row in enumerate(rows[1:], 1):  # Skip header
                try:
                    cells = row.find_elements(By.CSS_SELECTOR, '[role="cell"], .cell, .column')
                    if len(cells) >= 7:
                        subscription = {
                            'ID': cells[0].text.strip() if len(cells) > 0 else '',
                            'ID_client': cells[1].text.strip() if len(cells) > 1 else '',
                            'Email': cells[2].text.strip() if len(cells) > 2 else '',
                            'Numero_contact': cells[3].text.strip() if len(cells) > 3 else '',
                            'Type_abonnement': cells[4].text.strip() if len(cells) > 4 else '',
                            'Date_debut': cells[5].text.strip() if len(cells) > 5 else '',
                            'Date_fin': cells[6].text.strip() if len(cells) > 6 else '',
                            'Status': cells[7].text.strip() if len(cells) > 7 else '',
                            'Date_creation': cells[8].text.strip() if len(cells) > 8 else ''
                        }
                        subscriptions.append(subscription)
                except:
                    pass
            
            if subscriptions:
                print(f"      ✅ {len(subscriptions)} abonnements extraits")
                return subscriptions
                
        except Exception as e:
            print(f"      ⚠️ Erreur: {e}")
        
        # Méthode 4: Debug - Afficher la structure
        print("\n   📊 Structure de la page:")
        try:
            html = self.driver.page_source
            print(f"      Taille HTML: {len(html)} caractères")
            print(f"      Contient 'subscription': {'subscription' in html.lower()}")
            print(f"      Contient 'abonnement': {'abonnement' in html.lower()}")
            
            # Sauvegarder le HTML complet
            with open('page_full_debug.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("      💾 HTML complet sauvegardé: page_full_debug.html")
            
            # Screenshot
            self.driver.save_screenshot('page_screenshot.png')
            print("      📸 Screenshot sauvegardé: page_screenshot.png")
            
        except Exception as e:
            print(f"      ⚠️ Erreur debug: {e}")
        
        return subscriptions
    
    def scrape_all(self):
        """Pipeline complet de scraping"""
        self.wait_for_data_to_load()
        subscriptions = self.extract_subscriptions()
        return subscriptions
    
    def save_results(self, data):
        """Sauvegarde les résultats"""
        if not data:
            print("\n❌ Aucune donnée à sauvegarder")
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        df = pd.DataFrame(data)
        
        # CSV
        csv_filename = f'subscriptions_{timestamp}.csv'
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"\n✅ CSV: {csv_filename}")
        
        # Excel
        try:
            excel_filename = f'subscriptions_{timestamp}.xlsx'
            df.to_excel(excel_filename, index=False, engine='openpyxl')
            print(f"✅ Excel: {excel_filename}")
        except:
            pass
        
        # JSON
        json_filename = f'subscriptions_{timestamp}.json'
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON: {json_filename}")
        
        # Stats
        print(f"\n📊 STATISTIQUES")
        print(f"   Total: {len(df)} abonnements")
        
        for col in ['Status', 'Type_abonnement']:
            if col in df.columns:
                print(f"\n   Par {col}:")
                for val, count in df[col].value_counts().items():
                    print(f"      • {val}: {count}")
        
        print(f"\n📋 APERÇU:")
        print(df.head().to_string())
        
        return df
    
    def close(self):
        """Ferme le driver"""
        print("\n🔒 Fermeture du navigateur...")
        self.driver.quit()


# ==========================================
# EXÉCUTION
# ==========================================

print("=" * 70)
print("🚀 SCRAPER SELENIUM - BO APPELOFFRES.NET")
print("=" * 70)

EMAIL = 'chourouk.chaker6@gmail.com'
PASSWORD = 'CHAkerTun097@#'

scraper = None

try:
    scraper = AppelOffresSeleniumScraper()
    
    if scraper.login(EMAIL, PASSWORD):
        print("\n" + "=" * 70)
        print("✅ CONNEXION RÉUSSIE!")
        print("=" * 70)
        
        if scraper.navigate_to_subscriptions():
            subscriptions = scraper.scrape_all()
            
            if subscriptions:
                print(f"\n🎉 {len(subscriptions)} abonnements récupérés!")
                scraper.save_results(subscriptions)
                
                print("\n" + "=" * 70)
                print("✅ SCRAPING TERMINÉ!")
                print("=" * 70)
            else:
                print("\n⚠️ Aucune donnée extraite")
                print("💡 Vérifiez les fichiers de debug:")
                print("   - page_full_debug.html")
                print("   - page_screenshot.png")
    else:
        print("\n❌ Échec de la connexion")
        
except Exception as e:
    print(f"\n❌ Erreur fatale: {e}")
    import traceback
    traceback.print_exc()

finally:
    if scraper:
        scraper.close()

print("\n✅ Terminé")