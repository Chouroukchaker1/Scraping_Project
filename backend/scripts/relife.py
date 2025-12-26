#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRAPER RELIEFWEB - Extraction des offres d'emploi du 23 décembre 2025
Version avec valeurs par défaut
"""

# === IMPORTS DE BASE ===
import sys
import subprocess
import time
import json
import re
import random
import logging
import traceback
from datetime import datetime
import urllib.parse

print("="*70)
print("🚀 DÉMARRAGE DU SCRAPER RELIEFWEB - 23 DÉCEMBRE 2025")
print("="*70 + "\n")

# === FONCTION D'INSTALLATION DES PACKAGES ===
def installer_packages():
    """Installe les packages nécessaires avant de les importer"""
   
    packages_requis = [
        'requests',
        'pandas',
        'openpyxl',
        'beautifulsoup4',
        'lxml',
    ]
   
    packages_optionnels = [
        'cloudscraper',
        'fake-useragent',
        'selenium',
        'webdriver-manager',
        'googletrans==3.1.0a0',
    ]
   
    print("🔍 Vérification et installation des packages...")
    print("-" * 50)
   
    packages_installes = []
   
    def installer_package(package):
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--quiet"])
            return True
        except subprocess.CalledProcessError:
            return False
   
    for package in packages_requis:
        try:
            nom_import = package.replace('-', '_')
            __import__(nom_import)
            print(f"✅ {package} est déjà installé")
            packages_installes.append(package)
        except ImportError:
            print(f"📦 Installation de {package}...")
            if installer_package(package):
                print(f"✅ {package} installé avec succès")
                packages_installes.append(package)
            else:
                print(f"❌ Échec de l'installation de {package}")
                sys.exit(1)
   
    print("\n📦 Installation des packages optionnels...")
    print("-" * 50)
   
    for package in packages_optionnels:
        try:
            nom_import = package.replace('-', '_')
            __import__(nom_import)
            print(f"✅ {package} est déjà installé")
            packages_installes.append(package)
        except ImportError:
            print(f"⚙️  Installation de {package} (optionnel)...")
            if installer_package(package):
                print(f"✅ {package} installé")
                packages_installes.append(package)
            else:
                print(f"⚠️  {package} non installé (optionnel)")
   
    print(f"\n📊 Résumé: {len(packages_installes)}/{len(packages_requis + packages_optionnels)} packages installés")
    return packages_installes

# Exécuter l'installation
packages_installes = installer_packages()

print("\n" + "="*70)
print("📦 IMPORT DES PACKAGES...")
print("="*70)

# === IMPORT DES PACKAGES INSTALLÉS ===
try:
    import requests
    import pandas as pd
    from bs4 import BeautifulSoup
    print("✅ Packages principaux importés avec succès")
except ImportError as e:
    print(f"❌ Erreur critique d'import: {e}")
    sys.exit(1)

# Vérifier les packages optionnels
FAKE_USERAGENT_AVAILABLE = False
CLOUDSCRAPER_AVAILABLE = False
SELENIUM_AVAILABLE = False
TRANSLATOR_AVAILABLE = False

# Fake UserAgent
try:
    from fake_useragent import UserAgent
    FAKE_USERAGENT_AVAILABLE = True
    print("✅ Fake UserAgent importé")
except ImportError:
    print("⚠️ Fake UserAgent non disponible")

# Cloudscraper
try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
    print("✅ Cloudscraper importé")
except ImportError:
    print("⚠️ Cloudscraper non disponible")

# Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
    print("✅ Selenium importé")
except ImportError:
    print("⚠️ Selenium non disponible")

# Traducteur
try:
    from googletrans import Translator
    TRANSLATOR_AVAILABLE = True
    print("✅ Googletrans importé (pour la traduction)")
except ImportError:
    print("⚠️ Googletrans non disponible - les traductions seront limitées")

# === CONFIGURATION DU LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('reliefweb_scraper.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# === CLASSE PRINCIPALE DU SCRAPER ===
class ReliefWebScraperAdvanced:
    """Scraper avancé pour ReliefWeb avec filtre par date (23 décembre 2025)"""
   
    def __init__(self, target_date="2025-12-23"):
        self.api_url = "https://api.reliefweb.int/v1/jobs"
        self.web_url = "https://reliefweb.int/jobs"
        self.target_date = target_date
       
        # VALEURS PAR DÉFAUT AJOUTÉES
        self.default_values = {
            'Avis': 'Avis de candidature',
            'Source': 'Relief',
            'Type': 'National',
            'Nature': 'Privé/PPP/Autres',
            'Type_Source_Financement': 'National'
        }
       
        # Initialiser UserAgent si disponible
        self.use_fake_useragent = FAKE_USERAGENT_AVAILABLE
        if self.use_fake_useragent:
            try:
                self.ua = UserAgent(fallback="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                print("✅ Fake UserAgent initialisé")
            except:
                self.use_fake_useragent = False
                print("⚠️ Fake UserAgent échoué, utilisation d'agents statiques")
        else:
            print("ℹ️ Utilisation d'agents utilisateurs statiques")
       
        # Initialiser le traducteur si disponible
        self.translator_available = TRANSLATOR_AVAILABLE
        if self.translator_available:
            try:
                self.translator = Translator()
                print("✅ Traducteur Googletrans initialisé")
            except:
                self.translator_available = False
                print("⚠️ Traducteur échoué à l'initialisation")
        else:
            print("ℹ️ Traducteur non disponible - utilisation de traductions manuelles")
       
        # Vérifier la disponibilité des packages optionnels
        self.selenium_available = SELENIUM_AVAILABLE
        self.cloudscraper_available = CLOUDSCRAPER_AVAILABLE
       
        # Créer des sessions avec différents headers
        self.sessions = []
        self._init_sessions()
       
        # Dictionnaire de traductions manuelles
        self.translations_dict = {
            # Traductions de pays
            'Afghanistan': 'Afghanistan',
            'Bangladesh': 'Bangladesh',
            'Cameroon': 'Cameroun',
            'Chad': 'Tchad',
            'Colombia': 'Colombie',
            'Congo': 'Congo',
            'Democratic Republic of the Congo': 'République démocratique du Congo',
            'Ethiopia': 'Éthiopie',
            'Haiti': 'Haïti',
            'Iraq': 'Irak',
            'Jordan': 'Jordanie',
            'Kenya': 'Kenya',
            'Lebanon': 'Liban',
            'Libya': 'Libye',
            'Mali': 'Mali',
            'Mauritania': 'Mauritanie',
            'Myanmar': 'Myanmar',
            'Niger': 'Niger',
            'Nigeria': 'Nigéria',
            'Pakistan': 'Pakistan',
            'Palestine': 'Palestine',
            'Somalia': 'Somalie',
            'South Sudan': 'Soudan du Sud',
            'Sudan': 'Soudan',
            'Syria': 'Syrie',
            'Turkey': 'Turquie',
            'Uganda': 'Ouganda',
            'Ukraine': 'Ukraine',
            'Yemen': 'Yémen',
            'Zimbabwe': 'Zimbabwe',
           
            # Mots clés courants
            'Coordinator': 'Coordinateur',
            'Manager': 'Gestionnaire',
            'Officer': 'Agent',
            'Assistant': 'Assistant',
            'Specialist': 'Spécialiste',
            'Advisor': 'Conseiller',
            'Consultant': 'Consultant',
            'Director': 'Directeur',
            'Head': 'Chef',
            'Team Leader': 'Chef d\'équipe',
            'Project': 'Projet',
            'Program': 'Programme',
            'Emergency': 'Urgence',
            'Humanitarian': 'Humanitaire',
            'Development': 'Développement',
            'Field': 'Terrain',
            'Senior': 'Principal',
            'Junior': 'Junior',
            'National': 'National',
            'International': 'International',
            'Regional': 'Régional',
        }
       
        logger.info(f"🔧 Scraper initialisé - Date cible: {target_date}")
        logger.info(f"📋 Valeurs par défaut: {self.default_values}")
   
    def clean_job_data(self, job):
        """Nettoyer les données d'une offre d'emploi et ajouter les valeurs par défaut"""
        if not job:
            return job
       
        clean_job = job.copy()
       
        # Nettoyer toutes les valeurs
        for key in clean_job.keys():
            if isinstance(clean_job[key], str):
                # Supprimer les balises HTML
                clean_job[key] = re.sub(r'<[^>]+>', '', clean_job[key])
                # Supprimer les espaces en trop
                clean_job[key] = ' '.join(clean_job[key].split())
                # Remplacer NaN
                if clean_job[key].lower() == 'nan':
                    clean_job[key] = 'Non spécifié'
           
            # Convertir en string si ce n'est pas déjà le cas
            elif clean_job[key] is None:
                clean_job[key] = 'Non spécifié'
            else:
                clean_job[key] = str(clean_job[key])
       
        # AJOUTER LES VALEURS PAR DÉFAUT
        for key, value in self.default_values.items():
            if key not in clean_job:
                clean_job[key] = value
       
        return clean_job
   
    def _format_title(self, original_title):
        """Formater le titre pour qu'il commence par 'Recrutement d'un'"""
        if not original_title or original_title == 'Non spécifié':
            return "Recrutement d'un poste"
       
        title = str(original_title).strip()
       
        # Nettoyer les balises HTML
        title = re.sub(r'<[^>]+>', '', title)
       
        # Supprimer les points à la fin
        title = title.rstrip('.')
       
        # Traduire certains termes si nécessaire
        title = self._translate_text(title)
       
        # Déterminer si on utilise "d'un" ou "d'une"
        title_lower = title.lower()
       
        # Liste de mots féminins (avec déterminant "une")
        feminine_words_with_article = [
            'assistante', 'coordinatrice', 'directrice', 'gestionnaire',
            'responsable', 'chargée', 'technicienne', 'spécialiste',
            'consultante', 'analyste', 'administratrice', 'cheffe',
            'adjointe', 'superviseure', 'conseillère', 'gérante',
            'secrétaire', 'opératrice', 'ingénieure', 'chercheuse'
        ]
       
        # Vérifier si c'est clairement féminin
        use_feminine = False
        for word in feminine_words_with_article:
            if word in title_lower:
                use_feminine = True
                break
       
        # Si le titre commence par un mot féminin
        first_word = title_lower.split()[0] if title_lower.split() else ""
        if first_word in feminine_words_with_article:
            use_feminine = True
       
        # Formater le titre
        if use_feminine:
            # Supprimer "Recrutement de/d'une" si déjà présent
            if title_lower.startswith('recrutement de '):
                title = title[15:]
            elif title_lower.startswith('recrutement d\'une '):
                title = title[18:]
            elif title_lower.startswith('recrutement d\'un '):
                title = title[17:]
           
            # Capitaliser la première lettre
            if title:
                title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()
                formatted_title = f"Recrutement d'une {title}"
            else:
                formatted_title = "Recrutement d'une poste"
        else:
            # Supprimer "Recrutement de/d'un" si déjà présent
            if title_lower.startswith('recrutement de '):
                title = title[15:]
            elif title_lower.startswith('recrutement d\'un '):
                title = title[17:]
            elif title_lower.startswith('recrutement d\'une '):
                title = title[18:]
           
            # Capitaliser la première lettre
            if title:
                title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()
                formatted_title = f"Recrutement d'un {title}"
            else:
                formatted_title = "Recrutement d'un poste"
       
        return formatted_title
   
    def _create_description(self, formatted_title):
        """Créer une description - SIMPLIFIÉE POUR ÊTRE ÉGALE AU TITRE"""
        # Description = Titre uniquement (sans autres informations)
        return formatted_title
   
    def _extract_organization(self, fields, body_text=""):
        """Extraire et formater l'organisation (Promoteur) - VERSION AMÉLIORÉE"""
       
        # 1. Vérifier le champ 'source' (c'est la source/organisation qui publie l'offre)
        if 'source' in fields:
            source_data = fields['source']
           
            # Le champ source est un tableau d'objets
            if isinstance(source_data, list) and source_data:
                for source_item in source_data:
                    if isinstance(source_item, dict):
                        # Essayer d'abord le nom complet (longname)
                        if 'longname' in source_item:
                            org_name = source_item['longname']
                            if org_name and isinstance(org_name, str) and org_name.strip():
                                organisation = org_name.strip()
                                logger.debug(f"✅ Organisation trouvée dans source[longname]: {organisation}")
                                return self._clean_organization_name_no_translation(organisation)
                       
                        # Sinon utiliser le nom court (name)
                        if 'name' in source_item:
                            org_name = source_item['name']
                            if org_name and isinstance(org_name, str) and org_name.strip():
                                organisation = org_name.strip()
                                logger.debug(f"✅ Organisation trouvée dans source[name]: {organisation}")
                                return self._clean_organization_name_no_translation(organisation)
       
        # 2. Si pas trouvé, chercher 'host' (organisation hôte)
        if 'host' in fields:
            host_data = fields['host']
            if isinstance(host_data, list) and host_data:
                for host_item in host_data:
                    if isinstance(host_item, dict) and 'name' in host_item:
                        org_name = host_item['name']
                        if org_name and isinstance(org_name, str) and org_name.strip():
                            organisation = org_name.strip()
                            logger.debug(f"✅ Organisation trouvée dans host[name]: {organisation}")
                            return self._clean_organization_name_no_translation(organisation)
       
        # 3. Analyser plus en profondeur le texte du corps pour trouver l'organisation
        if body_text:
            organisation = self._deep_search_organization_in_text(body_text)
            if organisation != 'Non spécifié' and organisation != 'Organization':
                return self._clean_organization_name_no_translation(organisation)
       
        # 4. Fallback: chercher dans le texte avec des patterns simples
        organisation = self._search_organization_in_text(body_text)
        if organisation != 'Non spécifié' and organisation != 'Organization':
            return self._clean_organization_name_no_translation(organisation)
       
        return 'Non spécifié'
   
    def _deep_search_organization_in_text(self, body_text):
        """Recherche approfondie de l'organisation dans le texte"""
        if not body_text:
            return 'Non spécifié'
       
        clean_text = re.sub(r'<[^>]+>', ' ', body_text)
        clean_text = re.sub(r'\s+', ' ', clean_text)
       
        # Liste des patterns améliorés pour trouver l'organisation
        patterns = [
            # Patterns pour trouver l'organisation dans différents formats
            r'(?:Organization|Organisation|Agency|Employer|Source|Posted by)[:\s]+([^<\n\.]{3,80})',
            r'\b(?:UN|WFP|WHO|UNICEF|UNDP|UNHCR|OCHA|FAO|UNESCO|ILO|IOM|IFRC|ICRC|MSF|IRC|CRS|CARE|OXFAM|ACTED|DRC|NRC|SC|HI|MDM|ALIMA|IMC|GAN)\b',
            r'\b(?:International|National|Global|Regional|Humanitarian|Development|Agency|Organization|Council|Fund|Program|Service)s?\b[\s-]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})',
            r'©\s*([^<\n]{3,60})',
            r'All rights reserved[.\s]*([^<\n]{3,60})',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s+(?:Organization|Organisation|Agency|Council|Fund|Program)',
        ]
       
        for pattern in patterns:
            matches = re.findall(pattern, clean_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, str):
                    org = match.strip()
                    if org and len(org) >= 3 and org.lower() not in ['the', 'and', 'for', 'with']:
                        # Nettoyer l'organisation
                        org = re.sub(r'^\W+|\W+$', '', org)
                        if org and org != 'Organization':
                            logger.debug(f"🔍 Organisation trouvée via deep search: {org}")
                            return org
       
        return 'Non spécifié'
   
    def _clean_organization_name_no_translation(self, org_name):
        """Nettoyer le nom de l'organisation SANS traduction"""
        if not org_name or org_name == 'Non spécifié':
            return 'Non spécifié'
       
        # Nettoyer les balises HTML
        org_name = re.sub(r'<[^>]+>', '', org_name)
        # Supprimer les espaces en trop
        org_name = ' '.join(org_name.split())
        # Supprimer la ponctuation en fin
        org_name = org_name.rstrip('.,;:')
       
        # Éviter les valeurs génériques
        if org_name.lower() in ['organization', 'organisation', 'agency', 'employer', 'source']:
            return 'Non spécifié'
       
        return org_name[:100]
   
    def _search_organization_in_text(self, body_text):
        """Chercher l'organisation dans le texte du body"""
        if not body_text:
            return 'Non spécifié'
       
        clean_text = re.sub(r'<[^>]+>', ' ', body_text)
        clean_text = re.sub(r'\s+', ' ', clean_text)
       
        patterns = [
            r'Organization[:\s]+([^<\n]{3,100})',
            r'Organisation[:\s]+([^<\n]{3,100})',
            r'Posted by[:\s]+([^<\n]{3,100})',
            r'Source[:\s]+([^<\n]{3,100})',
            r'Employer[:\s]+([^<\n]{3,100})',
            r'\b[A-Z]{2,6}\b',
        ]
       
        for pattern in patterns:
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                if len(match.groups()) > 0:
                    org = match.group(1).strip()
                else:
                    org = match.group(0).strip()
                if org and len(org) >= 2:
                    if re.match(r'^[A-Z]{2,6}$', org.upper()):
                        return org.upper()
                    return org
       
        return 'Non spécifié'
   
    def _translate_text(self, text):
        """Traduire un texte en français en utilisant googletrans ou le dictionnaire de fallback"""
        if not text or text == 'Non spécifié':
            return text
       
        text = str(text).strip()
       
        if self.translator_available:
            try:
                translation = self.translator.translate(text, dest='fr')
                if translation and hasattr(translation, 'text'):
                    return translation.text
            except Exception as e:
                logger.debug(f"Erreur de traduction googletrans pour '{text}': {e}")
       
        if text in self.translations_dict:
            return self.translations_dict[text]
       
        for key, translation in self.translations_dict.items():
            if key.lower() == text.lower():
                return translation
            if key in text:
                text = text.replace(key, translation)
       
        return text
   
    def _init_sessions(self):
        """Initialiser plusieurs sessions avec différents headers"""
        headers_list = [
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': 'https://reliefweb.int/',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
            },
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'fr-FR,fr;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
        ]
       
        for headers in headers_list:
            try:
                session = requests.Session()
                session.headers.update(headers)
                self.sessions.append(session)
            except Exception as e:
                logger.warning(f"Erreur création session: {e}")
   
    def _get_random_session(self):
        """Obtenir une session aléatoire"""
        if not self.sessions:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'fr-FR,fr;q=0.9',
            })
            return session
        return random.choice(self.sessions)
   
    def _is_target_date(self, date_str):
        """Vérifier si une date correspond au 23 décembre 2025"""
        if not date_str or str(date_str).strip() in ['N/A', '', 'None', 'Non spécifié']:
            return False
       
        date_str = str(date_str).strip()
       
        date_formats = [
            "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d %b %Y", "%d %B %Y",
            "%b %d, %Y", "%B %d, %Y", "%Y-%m-dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
            "%d-%m-%Y", "%Y/%m/%d",
        ]
       
        for date_format in date_formats:
            try:
                clean_date = date_str.split('T')[0].split(' ')[0]
                date_obj = datetime.strptime(clean_date, date_format)
                if date_obj.day == 23 and date_obj.month == 12 and date_obj.year == 2025:
                    return True
            except (ValueError, IndexError):
                continue
       
        date_lower = date_str.lower()
        date_patterns = [
            "23 dec 2025", "dec 23 2025", "23 décembre 2025", "décembre 23 2025",
            "23/12/2025", "12/23/2025", "23-12-2025", "12-23-2025",
            "2025-12-23", "2025/12/23", "23.12.2025", "12.23.2025"
        ]
       
        for pattern in date_patterns:
            if pattern in date_lower:
                return True
       
        return False
   
    def method_1_api_official(self):
        """Méthode 1: API officielle de ReliefWeb"""
        logger.info("\n" + "="*70)
        logger.info("📡 MÉTHODE 1: API Officielle ReliefWeb")
        logger.info("="*70)
       
        jobs = []
       
        try:
            params = {
                "appname": "reliefweb-jobs-scraper",
                "profile": "full",
                "limit": 150,
                "offset": 0,
                "sort[]": "date.created:desc",
                "filter[field]": "date.created",
                "filter[value]": f"[{self.target_date}T00:00:00 TO {self.target_date}T23:59:59]",
                "fields[include]": ["title", "url", "source", "host", "country", "date.created", "date.closing", "body"],
                "filter[operator]": "AND",
                "filter[status]": "open",
                "format": "json",
            }
           
            logger.info(f"🔍 Requête API pour le {self.target_date}")
           
            session = self._get_random_session()
            response = session.get(self.api_url, params=params, timeout=45, verify=True)
           
            logger.info(f"📊 Statut HTTP: {response.status_code}")
           
            if response.status_code == 200:
                try:
                    data = response.json()
                   
                    if 'data' in data and data['data']:
                        items = data['data']
                        logger.info(f"✅ {len(items)} items trouvés dans l'API")
                       
                        for item in items:
                            job = self._extract_from_api_item(item)
                            if job:
                                jobs.append(job)
                       
                        logger.info(f"🎯 {len(jobs)} offres du {self.target_date} extraites")
                       
                        org_missing = sum(1 for j in jobs if j['Promoteur'] in ['Organization', 'Non spécifié', 'organisation'])
                        if org_missing > 0:
                            logger.warning(f"⚠️ {org_missing} offres avec organisation manquante ou générique")
                    else:
                        logger.warning("⚠️ Aucune donnée trouvée dans la réponse API")
                       
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Erreur JSON: {e}")
            else:
                logger.error(f"❌ Erreur HTTP {response.status_code}")
               
        except Exception as e:
            logger.error(f"❌ Erreur API: {e}")
            logger.error(traceback.format_exc())
       
        return jobs
   
    def _extract_from_api_item(self, item):
        """Extraire les données d'un item de l'API"""
        try:
            fields = item.get('fields', {})
           
            # Titre original
            original_title = fields.get('title', '').strip()
            if not original_title:
                return None
           
            logger.debug(f"Titre original: {original_title[:50]}...")
           
            # Formater le titre
            title = self._format_title(original_title)
           
            # URL
            url = fields.get('url', '')
            if not url:
                return None
           
            # Extraire l'organisation
            body_text = fields.get('body', '')
            organisation = self._extract_organization(fields, body_text)
           
            # Si l'organisation est générique
            if organisation in ['Organization', 'organisation']:
                organisation = 'Non spécifié'
           
            logger.info(f"🔍 Organisation extraite: {organisation}")
           
            # Date de création
            date_info = fields.get('date', {})
            date_created = date_info.get('created', '')
           
            # Vérifier la date
            if not self._is_target_date(date_created):
                return None
           
            # Date d'expiration
            date_expiration = date_info.get('closing', 'Non spécifié')
            if date_expiration == 'Non spécifié' and body_text:
                expiration_patterns = [
                    r'closing\s*date[:\s]*(\d{1,2}\s+\w+\s+\d{4})',
                    r'deadline[:\s]*(\d{1,2}\s+\w+\s+\d{4})',
                    r'date\s*limite[:\s]*(\d{1,2}\s+\w+\s+\d{4})',
                ]
                for pattern in expiration_patterns:
                    match = re.search(pattern, body_text, re.IGNORECASE)
                    if match:
                        date_expiration = match.group(1)
                        break
           
            # Pays
            countries = fields.get('country', [])
            pays_list = []
            for country in countries:
                if isinstance(country, dict):
                    country_name = country.get('name', '').strip()
                    if country_name:
                        pays_list.append(self._translate_text(country_name))
                elif isinstance(country, str):
                    if country.strip():
                        pays_list.append(self._translate_text(country.strip()))
           
            pays = ', '.join(pays_list) if pays_list else 'Non spécifié'
           
            # Description simplifiée
            description = self._create_description(title)
           
            # CRÉER LE DICTIONNAIRE DE DONNÉES AVEC TOUS LES CHAMPS
            job_data = {
                'Titre': title[:200],
                'URL': url,
                'Promoteur': organisation[:100],
                'Pays': pays[:200],
                'Date_publication': date_created,
                'Date_expiration': date_expiration,
                'Description': description[:200],
                'Source': 'API ReliefWeb',
                'Methode_extraction': 'API officielle',
                # AJOUT DES VALEURS PAR DÉFAUT DIRECTEMENT DANS L'EXTRACTION
                'Avis': self.default_values['Avis'],
                'Source_Financement': self.default_values['Source'],
                'Type': self.default_values['Type'],
                'Nature': self.default_values['Nature'],
                'Type_Source_Financement': self.default_values['Type_Source_Financement']
            }
           
            logger.debug(f"✅ Job extrait: {title[:50]}... | Promoteur: {organisation}")
           
            return job_data
           
        except Exception as e:
            logger.error(f"❌ Erreur extraction API: {e}")
            return None
   
    def method_2_web_scraping(self):
        """Méthode 2: Scraping web direct"""
        logger.info("\n" + "="*70)
        logger.info("🌐 MÉTHODE 2: Scraping Web Direct")
        logger.info("="*70)
       
        jobs = []
       
        urls_to_try = [
            f"https://reliefweb.int/jobs?date={self.target_date}",
            f"https://reliefweb.int/jobs?date[from]={self.target_date}&date[to]={self.target_date}",
            f"https://reliefweb.int/jobs?created={self.target_date}",
            "https://reliefweb.int/jobs?sort=date",
        ]
       
        for url in urls_to_try:
            try:
                logger.info(f"🌐 Tentative avec: {url}")
               
                session = self._get_random_session()
                response = session.get(url, timeout=30)
               
                if response.status_code == 200:
                    if "JavaScript is disabled" in response.text:
                        logger.warning("🚫 Page bloquée (JavaScript requis)")
                        continue
                   
                    soup = BeautifulSoup(response.content, 'lxml')
                    parsed_jobs = self._parse_html_page(soup, url)
                   
                    filtered_jobs = []
                    for job in parsed_jobs:
                        if self._is_target_date(job['Date_publication']):
                            filtered_jobs.append(job)
                   
                    if filtered_jobs:
                        logger.info(f"✅ {len(filtered_jobs)} offres du {self.target_date} trouvées")
                        jobs.extend(filtered_jobs)
                        break
                    else:
                        logger.info(f"⚠️ Aucune offre du {self.target_date} sur cette URL")
               
                elif response.status_code in [403, 429, 503]:
                    logger.warning(f"Erreur HTTP {response.status_code}")
                    time.sleep(5 if response.status_code == 429 else 3)
               
                time.sleep(random.uniform(2, 4))
               
            except Exception as e:
                logger.error(f"❌ Erreur avec {url}: {e}")
                continue
       
        return jobs
   
    def _parse_html_page(self, soup, base_url):
        """Parser une page HTML"""
        jobs = []
       
        selectors = [
            ('article', {'class': re.compile(r'job|listing|item|card|teaser|rw-river-article')}),
            ('div', {'class': re.compile(r'job-\w+|listing-\w+|rw-\w+|river--job')}),
            ('li', {'class': re.compile(r'job|listing|item|rw-river-article')}),
            ('section', {'class': re.compile(r'jobs|listings|content|rw-river')}),
        ]
       
        for tag, attrs in selectors:
            elements = soup.find_all(tag, attrs)
            if elements:
                logger.info(f"🔍 Sélecteur {tag}: {len(elements)} éléments trouvés")
               
                for element in elements:
                    job = self._extract_from_html_element(element)
                    if job:
                        if job['URL'] and not job['URL'].startswith('http'):
                            job['URL'] = urllib.parse.urljoin(base_url, job['URL'])
                        jobs.append(job)
               
                if jobs:
                    break
       
        return jobs
   
    def _extract_from_html_element(self, element):
        """Extraire les données d'un élément HTML"""
        try:
            # Titre
            title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'span'],
                                     class_=re.compile(r'title|heading|name|job-title'))
            original_title = title_elem.get_text(strip=True) if title_elem else None
           
            if not original_title:
                original_title = element.get_text(strip=True)[:100].strip()
                if len(original_title) < 15:
                    return None
           
            # Formater le titre
            title = self._format_title(original_title)
           
            # Lien
            link_elem = element.find('a', href=True)
            url = link_elem['href'] if link_elem else ''
           
            # Organisation
            organisation = 'Non spécifié'
            org_selectors = [
                {'class': re.compile(r'org|source|company|agency|employer|organization')},
                {'data-org': True},
                {'data-source': True},
            ]
           
            for selector in org_selectors:
                if 'class' in selector:
                    org_elem = element.find(class_=selector['class'])
                elif 'data-org' in selector:
                    org_elem = element.find(attrs={'data-org': True})
                elif 'data-source' in selector:
                    org_elem = element.find(attrs={'data-source': True})
               
                if org_elem:
                    if 'data-org' in selector or 'data-source' in selector:
                        organisation = org_elem.get(list(selector.keys())[0], '').strip()
                    else:
                        organisation = org_elem.get_text(strip=True)
                   
                    if organisation and len(organisation) > 2:
                        organisation = self._clean_organization_name_no_translation(organisation)
                        if organisation != 'Non spécifié':
                            break
           
            # Date de publication
            date_elem = element.find('time') or element.find(class_=re.compile(r'date|time|posted|created'))
            date_str = date_elem.get_text(strip=True) if date_elem else ''
           
            # Date d'expiration
            date_expiration = 'Non spécifié'
            element_text_full = element.get_text()
           
            expiration_patterns = [
                r'date\s*limite[:\s]*(\d{1,2}\s+\w+\s+\d{4})',
                r'cl[ôo]ture[:\s]*(\d{1,2}\s+\w+\s+\d{4})',
                r'deadline[:\s]*(\d{1,2}\s+\w+\s+\d{4})',
                r'closing\s*date[:\s]*(\d{1,2}\s+\w+\s+\d{4})',
            ]
           
            for pattern in expiration_patterns:
                match = re.search(pattern, element_text_full, re.IGNORECASE)
                if match:
                    date_expiration = match.group(1)
                    break
           
            # Localisation
            location_elem = element.find(class_=re.compile(r'country|location|place|city|region'))
            pays = location_elem.get_text(strip=True) if location_elem else 'Non spécifié'
            pays = self._translate_text(pays)
           
            # Description
            description = self._create_description(title)
           
            # CRÉER LE DICTIONNAIRE AVEC TOUS LES CHAMPS
            return {
                'Titre': title[:200],
                'URL': url,
                'Promoteur': organisation[:100],
                'Pays': pays[:100],
                'Date_publication': date_str or self.target_date,
                'Date_expiration': date_expiration,
                'Description': description[:200],
                'Source': 'ReliefWeb',
                'Methode_extraction': 'HTML parsing',
                # AJOUT DES VALEURS PAR DÉFAUT
                'Avis': self.default_values['Avis'],
                'Source_Financement': self.default_values['Source'],
                'Type': self.default_values['Type'],
                'Nature': self.default_values['Nature'],
                'Type_Source_Financement': self.default_values['Type_Source_Financement']
            }
        except Exception as e:
            logger.debug(f"Erreur extraction HTML: {e}")
            return None
   
    def scrape_jobs_for_date(self, max_results=100):
        """Utiliser toutes les méthodes disponibles pour extraire les offres"""
       
        logger.info("\n" + "="*70)
        logger.info(f"🎯 EXTRACTION TOUTES MÉTHODES - {self.target_date}")
        logger.info("="*70)
       
        all_jobs = []
        seen_urls = set()
       
        methods = [
            ("API Officielle", self.method_1_api_official),
            ("Scraping Web", self.method_2_web_scraping),
        ]
       
        for method_name, method_func in methods:
            if len(all_jobs) >= max_results:
                logger.info(f"✅ Objectif de {max_results} offres atteint")
                break
           
            logger.info(f"\n🔄 Tentative: {method_name}")
            try:
                jobs = method_func()
               
                if jobs:
                    new_jobs = 0
                    for job in jobs:
                        url = job.get('URL', '')
                        if url and url not in seen_urls:
                            # Nettoyer et ajouter les valeurs par défaut
                            clean_job = self.clean_job_data(job)
                            seen_urls.add(url)
                            all_jobs.append(clean_job)
                            new_jobs += 1
                   
                    logger.info(f"📈 {method_name}: {new_jobs} nouvelles offres")
                   
                    if new_jobs > 0 and len(jobs) > 0:
                        clean_title = re.sub(r'<[^>]+>', '', jobs[0]['Titre'])
                        clean_org = re.sub(r'<[^>]+>', '', jobs[0]['Promoteur'])
                        logger.info(f"   📌 Exemple: {clean_title[:60]}... | Promoteur: {clean_org}")
                else:
                    logger.info(f"⚠️ {method_name}: Aucune offre")
               
                time.sleep(random.uniform(2, 4))
               
            except Exception as e:
                logger.error(f"❌ {method_name} échouée: {e}")
                continue
       
        # Post-traitement
        for job in all_jobs:
            if job['Promoteur'] in ['Organization', 'organisation']:
                job['Promoteur'] = 'Non spécifié'
       
        # Trier par date d'expiration
        def sort_key(job):
            expiration = job.get('Date_expiration', '')
            publication = job.get('Date_publication', '')
            if expiration != 'Non spécifié':
                try:
                    return (0, expiration)
                except:
                    return (1, publication)
            return (1, publication)
       
        all_jobs.sort(key=sort_key)
        all_jobs = all_jobs[:max_results]
       
        # Statistiques
        org_missing = sum(1 for j in all_jobs if j['Promoteur'] == 'Non spécifié')
        org_found = len(all_jobs) - org_missing
       
        logger.info("\n" + "="*70)
        logger.info(f"📅 RÉSULTATS FINAUX: {len(all_jobs)} offres du {self.target_date}")
        logger.info(f"   ✅ Organisations trouvées: {org_found}")
        logger.info(f"   ⚠️ Organisations manquantes: {org_missing}")
        logger.info(f"   📋 Valeurs par défaut appliquées: {list(self.default_values.keys())}")
        logger.info("="*70)
       
        return all_jobs

# === FONCTION PRINCIPALE ===
def main():
    """Fonction principale d'exécution"""
   
    print("\n" + "="*70)
    print("🎯 EXTRACTION RELIEFWEB - OFFRES DU 23 DÉCEMBRE 2025")
    print("📋 AVEC VALEURS PAR DÉFAUT")
    print("="*70 + "\n")
   
    try:
        scraper = ReliefWebScraperAdvanced(target_date="2025-12-23")
       
        # Afficher les valeurs par défaut
        print("📋 VALEURS PAR DÉFAUT CONFIGURÉES:")
        print("-" * 40)
        for key, value in scraper.default_values.items():
            print(f"   • {key}: {value}")
        print()
       
        print("⏳ Début de l'extraction...")
        jobs_data = scraper.scrape_jobs_for_date(max_results=100)
       
        if not jobs_data:
            print("\n" + "="*70)
            print(f"❌ AUCUNE OFFRE TROUVÉE POUR LE 23 DÉCEMBRE 2025")
            print("="*70)
            return
       
        df = pd.DataFrame(jobs_data)
        df = df.fillna('Non spécifié')
       
        print("\n" + "="*70)
        print(f"📊 STATISTIQUES - {len(df)} OFFRES")
        print("="*70)
       
        if not df.empty:
            print(f"\n🏢 Promoteurs principaux:")
            org_counts = df['Promoteur'].value_counts().head(10)
            for org, count in org_counts.items():
                if org != 'Non spécifié':
                    print(f"   • {org}: {count} offre(s)")
           
            missing_org = (df['Promoteur'] == 'Non spécifié').sum()
            if missing_org > 0:
                print(f"\n⚠️ Offres sans promoteur identifié: {missing_org}")
           
            print(f"\n🌍 Pays de mission:")
            pays_counts = df['Pays'].value_counts().head(10)
            for pays, count in pays_counts.items():
                if pays != 'Non spécifié':
                    print(f"   • {pays}: {count} offre(s)")
           
            print(f"\n📊 Méthodes d'extraction:")
            method_counts = df['Methode_extraction'].value_counts()
            for method, count in method_counts.items():
                print(f"   • {method}: {count} offre(s)")
       
        print("\n" + "="*70)
        print("📋 LISTE DES OFFRES AVEC VALEURS PAR DÉFAUT")
        print("="*70)
       
        for idx, row in df.iterrows():
            print(f"\n{'='*60}")
            print(f"📌 OFFRE {idx + 1}/{len(df)}")
            print(f"{'='*60}")
           
            # Afficher toutes les colonnes
            for col in df.columns:
                value = str(row[col]).strip()
                value = re.sub(r'<[^>]+>', '', value)
                value = value.replace('nan', 'Non spécifié')
               
                if value and value != 'Non spécifié':
                    # Formater l'affichage selon la colonne
                    if col == 'Titre':
                        print(f"📝 {col}: {value}")
                    elif col == 'Promoteur':
                        print(f"🏢 {col}: {value}")
                    elif col == 'Pays':
                        print(f"🌍 {col}: {value}")
                    elif col in ['Date_publication', 'Date_expiration']:
                        print(f"📅 {col}: {value}")
                    elif col == 'Description':
                        print(f"📄 {col}: {value}")
                    elif col == 'URL':
                        print(f"🔗 {col}: {value}")
                    elif col in ['Avis', 'Source_Financement', 'Type', 'Nature', 'Type_Source_Financement']:
                        print(f"⚙️  {col}: {value} (valeur par défaut)")
                    else:
                        print(f"📊 {col}: {value}")
       
        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
       
        # Préparer le DataFrame pour l'export
        df_clean = df.copy()
        for col in df_clean.columns:
            df_clean[col] = df_clean[col].astype(str)
            df_clean[col] = df_clean[col].replace('nan', 'Non spécifié')
            df_clean[col] = df_clean[col].apply(lambda x: re.sub(r'<[^>]+>', '', str(x)))
       
        # Réorganiser les colonnes pour une meilleure lisibilité
        column_order = [
            'Titre', 'Promoteur', 'Pays', 'Date_publication', 'Date_expiration',
            'Description', 'URL', 'Avis', 'Source_Financement', 'Type',
            'Nature', 'Type_Source_Financement', 'Source', 'Methode_extraction'
        ]
       
        # Garder seulement les colonnes existantes
        existing_columns = [col for col in column_order if col in df_clean.columns]
        df_clean = df_clean[existing_columns]
       
        # Fichier CSV
        csv_file = f'offres_reliefweb_23decembre2025_{timestamp}.csv'
        df_clean.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"\n💾 Fichier CSV sauvegardé: {csv_file}")
       
        # Fichier Excel
        excel_file = f'offres_reliefweb_23decembre2025_{timestamp}.xlsx'
        df_clean.to_excel(excel_file, index=False)
        print(f"📊 Fichier Excel sauvegardé: {excel_file}")
       
        print("\n" + "="*70)
        print("✅ EXTRACTION TERMINÉE AVEC SUCCÈS!")
        print(f"📅 {len(df)} offres du 23 décembre 2025 extraites")
        print(f"🏢 {len(df) - missing_org} promoteurs identifiés")
        print(f"⚙️  Valeurs par défaut appliquées: {len(scraper.default_values)} champs")
        print("="*70)
       
    except KeyboardInterrupt:
        print("\n\n⏹️ Extraction interrompue")
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        traceback.print_exc()
        print("="*70)

# === POINT D'ENTRÉE ===
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🤖 SCRAPER RELIEFWEB - AVEC VALEURS PAR DÉFAUT")
    print("✅ Extraction des offres du 23 décembre 2025")
    print("✅ Valeurs par défaut appliquées automatiquement")
    print("="*70)
   
    main()
   
    print("\n🔚 Fin du script.")
    print("Merci d'avoir utilisé le scraper ReliefWeb!")   