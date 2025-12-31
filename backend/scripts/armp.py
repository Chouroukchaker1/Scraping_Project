#!/usr/bin/env python3
"""
Extracteur d'Appels d'Offres ARMP - Tous Secteurs - Version Corrigée avec PROMOTEUR
Analyse la vraie structure HTML avec tableaux du site ARMP
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime, timedelta
import time
import logging
from urllib.parse import urljoin, urlparse
import os
import json
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ARMPTableScraper:
    def __init__(self):
        self.base_url = "http://www.armp.mg/marches_publics/"
        self.session = requests.Session()
        
        # Headers pour simuler un navigateur réel
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'http://www.armp.mg/'
        })
    
    def parse_entite_fields(self, entite_text):
        """Divise le champ entite en ref, localisation, N° et PROMOTEUR avec parsing amélioré"""
        fields = {
            'ref': '',
            'localisation': '',
            'numero': '',
            'promoteur': ''
        }
        
        if not entite_text:
            return fields
        
        text = entite_text.strip()
        text_lower = text.lower()
        
        # Nettoyer les tirets multiples
        text = re.sub(r'-{2,}', ' - ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Pattern pour N° complet
        num_pattern = r'(N°|No|Numéro)\s*[:\-]?\s*([^\s].*?)(?=\s*(?:$|Objet|Date|Localisation|Mode|ENTITE|REF|À\s+|$))'
        num_match = re.search(num_pattern, text, re.IGNORECASE)
        if num_match:
            numero_raw = num_match.group(2).strip()
            # Nettoyer si commence par SIGMP: ou similaire
            numero_raw = re.sub(r'^(SIGMP|AMI|AO)\s*[:\-]?\s*', '', numero_raw, flags=re.IGNORECASE).strip()
            fields['numero'] = numero_raw
        
        # Pattern pour REF
        ref_pattern = r'(REF|Réf|Référence)\s*[:\-]?\s*([A-Z0-9/.-]+)'
        ref_match = re.search(ref_pattern, text, re.IGNORECASE)
        if ref_match:
            fields['ref'] = ref_match.group(2).strip()
        
        # Pattern pour Localisation
        loc_pattern = r'(Localisation|Lieu|Ville|à|de)\s*[:\-]?\s*([A-Za-zÀ-ÿ\s,-]+?)(?=\s*(?:$|Mode|N°|Objet|REF))'
        loc_match = re.search(loc_pattern, text, re.IGNORECASE)
        if loc_match:
            fields['localisation'] = loc_match.group(2).strip()
            # Nettoyer
            fields['localisation'] = re.sub(r'\s+', ' ', fields['localisation']).strip()
        
        # Pattern pour PROMOTEUR - Chercher les noms d'institutions/ministères
        promoteur_patterns = [
            r'(?:MINISTERE|MINISTÈRE)\s+(?:DE\s+)?([A-ZÀ-Ÿ\s]+?)(?:\s+DE\s+|$)',
            r'(?:DIRECTION|DIRECTEUR)\s+(?:DE|REGIONALE|REGION)\s+([A-ZÀ-Ÿ\s]+?)(?:\s+|$)',
            r'(?:TRIBUNAL|COUR|JUGE|JUSTICE)\s+([A-ZÀ-Ÿ\s]+?)(?:\s+|$)',
            r'(?:HOPITAL|HÔPITAL|CENTRE\s+MÉDICAL)\s+([A-ZÀ-Ÿ\s]+?)(?:\s+|$)',
            r'(?:ÉCOLE|SCHOOL|UNIVERSITÉ|INSTITUT)\s+([A-ZÀ-Ÿ\s]+?)(?:\s+|$)',
            r'(?:AGENCE|OFFICE|BUREAU|SERVICE)\s+([A-ZÀ-Ÿ\s]+?)(?:\s+|$)',
            r'([A-ZÀ-Ÿ]{2,}\s+[A-ZÀ-Ÿ\s]+?)(?:\s+(?:DE|DU|À|EN)\s+|$)',
            r'(?:PAOSTRA|PAOSTR)\s+([A-ZÀ-Ÿ\s]+?)(?:\s+|$)'
        ]
        
        for pattern in promoteur_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                promoteur_candidate = match.group(1).strip()
                # Nettoyer et vérifier si c'est un promoteur valide
                promoteur_candidate = re.sub(r'\s+', ' ', promoteur_candidate)
                # Éviter les faux positifs (références numériques, etc.)
                if len(promoteur_candidate) > 3 and not re.match(r'^\d+[A-Z\s]*$', promoteur_candidate):
                    fields['promoteur'] = promoteur_candidate
                    break
        
        # Fallback: extraire le promoteur depuis le début du texte (souvent le nom de l'entité)
        if not fields['promoteur']:
            # Prendre la première ligne ou la première partie significative
            lines = text.split('\n')
            first_line = lines[0].strip() if lines else text
            # Chercher un nom d'institution dans la première ligne
            inst_pattern = r'^([A-ZÀ-Ÿ\s]+?)(?:\s+REF|\s+N°|\s+Local|\s+Mode|$)'
            inst_match = re.search(inst_pattern, first_line, re.IGNORECASE)
            if inst_match:
                fields['promoteur'] = inst_match.group(1).strip()
            elif len(first_line) > 5:
                # Prendre les premières 30-50 caractères comme promoteur
                words = first_line.split()
                promoteur_words = words[:4]  # Prendre jusqu'à 4 mots
                fields['promoteur'] = ' '.join(promoteur_words)
        
        # Fallback: split par séparateurs pour les autres champs
        if not any([fields['ref'], fields['numero']]):
            parts = re.split(r'[,/-]\s*', text)
            cities = ['antananarivo', 'toamasina', 'fianarantsoa', 'mahajanga', 'toliara', 'antsiranana', 'centrale', 'sava', 'vatomandry', 'atovavy']
            for i, part in enumerate(parts):
                part_lower = part.lower().strip()
                if re.match(r'(n°|no|numéro)', part_lower):
                    fields['numero'] = ' '.join([p.strip() for p in parts[i+1:] if p.strip()]).strip()
                elif re.match(r'[a-z]{2,}/\d{4}', part, re.IGNORECASE):
                    fields['ref'] = part.strip()
                elif any(city in part_lower for city in cities):
                    fields['localisation'] = part.strip()
                # Si partie avec N° dedans
                num_in_part = re.search(r'(N°|No)\s*([^\s].*)', part)
                if num_in_part:
                    fields['numero'] = num_in_part.group(2).strip()
        
        # Nettoyer les champs
        for key in fields:
            if fields[key]:
                fields[key] = re.sub(r'\s+', ' ', fields[key]).strip()
                # Enlever tirets en fin
                fields[key] = re.sub(r'-\s*$', '', fields[key])
                # Capitaliser proprement le promoteur
                if key == 'promoteur':
                    fields[key] = fields[key].title()
        
        return fields
    
    def extract_dates_from_text(self, text):
        """Extrait toutes les dates importantes du texte"""
        dates = {
            'date_debut': None,
            'date_fin': None,
            'heure_limite': None
        }
        
        if not text:
            return dates
        
        # Patterns pour différents formats de dates
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\d{2}/\d{2}/\d{4})',  # DD/MM/YYYY
            r'(\d{2}-\d{2}-\d{4})',  # DD-MM-YYYY
        ]
        
        # Trouver toutes les dates dans le texte
        all_dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            all_dates.extend(matches)
        
        # Patterns contextuels
        context_patterns = {
            'debut': r'(?:du|début|commence|démarrage).*?(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})',
            'fin': r'(?:au|fin|termine|jusqu).*?(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})',
        }
        
        for date_type, pattern in context_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if date_type == 'debut':
                    dates['date_debut'] = match.group(1)
                elif date_type == 'fin':
                    dates['date_fin'] = match.group(1)
        
        # Extraire l'heure
        heure_patterns = [
            r'(\d{1,2}[hH]\d{2}(?:[mM]in)?)',
            r'(\d{1,2}:\d{2})',
            r'(\d{1,2}\s*[hH]\s*\d{2})'
        ]
        
        for pattern in heure_patterns:
            match = re.search(pattern, text)
            if match:
                dates['heure_limite'] = match.group(1)
                break
        
        # Si on a trouvé des dates sans contexte, les assigner intelligemment
        if all_dates and not any(dates.values()):
            if len(all_dates) >= 2:
                dates['date_debut'] = all_dates[0]
                dates['date_fin'] = all_dates[-1]
            elif len(all_dates) == 1:
                dates['date_fin'] = all_dates[0]
        
        return dates
    
    def get_page_content(self, url, timeout=30):
        """Récupère le contenu d'une page avec gestion d'erreur"""
        try:
            logger.info(f"Récupération de: {url}")
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la récupération de {url}: {e}")
            return None
    
    def extract_from_table(self, html_content):
        """Extrait les données depuis la structure de tableau HTML"""
        if not html_content:
            return []
        
        soup = BeautifulSoup(html_content, 'html.parser')
        appels_offres = []
        
        # Chercher toutes les tables
        tables = soup.find_all('table')
        logger.info(f"Nombre de tables trouvées: {len(tables)}")
        
        for table_idx, table in enumerate(tables):
            logger.info(f"Analyse de la table {table_idx + 1}")
            
            # Chercher les en-têtes (ENTITE, OBJET, DATE, ASAP)
            headers = []
            thead = table.find('thead')
            if thead:
                header_cells = thead.find_all(['th', 'td'])
                headers = [cell.get_text().strip().upper() for cell in header_cells]
                logger.info(f"En-têtes trouvés: {headers}")
            
            # Analyser les lignes de données
            tbody = table.find('tbody')
            if not tbody:
                # Si pas de tbody, analyser toutes les tr
                rows = table.find_all('tr')
            else:
                rows = tbody.find_all('tr')
            
            logger.info(f"Nombre de lignes de données: {len(rows)}")
            
            for row_idx, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:  # Ignorer les lignes avec trop peu de cellules
                    continue
                
                # Extraire le contenu des cellules
                cell_data = []
                for cell in cells:
                    cell_text = cell.get_text().strip()
                    # Chercher aussi les liens dans la cellule
                    links = cell.find_all('a', href=True)
                    cell_links = [urljoin(self.base_url, link['href']) for link in links if 'pdf' in link['href'].lower()]
                    cell_data.append({
                        'text': cell_text,
                        'links': cell_links
                    })
                
                if not cell_data:
                    continue
                
                # Construire l'objet appel d'offre
                appel = {}
                
                # Mapper les données selon l'ordre des colonnes
                if len(cell_data) >= 1:
                    entite_raw = cell_data[0]['text']
                    # Diviser l'entite en champs séparés (maintenant avec PROMOTEUR)
                    entite_fields = self.parse_entite_fields(entite_raw)
                    appel.update(entite_fields)
                if len(cell_data) >= 2:
                    appel['objet'] = cell_data[1]['text']
                if len(cell_data) >= 3:
                    appel['date_info'] = cell_data[2]['text']
                if len(cell_data) >= 4:
                    appel['asap'] = cell_data[3]['links'][0] if cell_data[3]['links'] else cell_data[3]['text']
                
                # Chercher des liens PDF dans toute la ligne
                all_links = []
                for cell_info in cell_data:
                    all_links.extend(cell_info['links'])
                
                if all_links and not appel.get('asap'):
                    appel['asap'] = all_links[0]
                elif not appel.get('asap'):
                    appel['asap'] = 'Non disponible'
                
                # Créer le texte complet pour l'analyse
                full_text = f"{appel.get('promoteur', '')} {appel.get('ref', '')} {appel.get('localisation', '')} {appel.get('numero', '')} {appel.get('objet', '')} {appel.get('date_info', '')}"
                
                # Extraire les dates
                dates = self.extract_dates_from_text(appel.get('date_info', ''))
                appel.update(dates)

                # Combiner heure_limite avec date_fin si possible
                if appel.get('heure_limite') and appel.get('date_fin'):
                    appel['date_fin'] = f"{appel['date_fin']} {appel['heure_limite']}"
                
                # Nettoyer les données
                for key, value in appel.items():
                    if isinstance(value, str):
                        appel[key] = re.sub(r'\s+', ' ', value).strip()
                
                if appel.get('objet'):
                    appels_offres.append(appel)
                    
                    logger.info(f"Offre extraite: {appel.get('promoteur', 'N/A')[:50]}...")
        
        return appels_offres
    
    def scrape_all_pages(self, max_pages=3):
        """Scrape plusieurs pages du site ARMP"""
        all_appels = []
        
        # URLs à tester
        urls_to_try = [
            self.base_url,
            self.base_url + "index.php",
            self.base_url + "consultation.php",
            "http://www.armp.mg/index.php",
            "http://www.armp.mg/consultation.php"
        ]
        
        for url in urls_to_try:
            logger.info(f"Test de l'URL: {url}")
            content = self.get_page_content(url)
            if content:
                appels = self.extract_from_table(content)
                if appels:
                    all_appels.extend(appels)
                    logger.info(f"✅ {len(appels)} offres trouvées sur {url}")
                    break  # Arrêter à la première URL qui fonctionne
                else:
                    logger.info(f"❌ Aucune offre sur {url}")
            
            time.sleep(1)  # Pause entre les requêtes
        
        # Supprimer les doublons
        seen_ids = set()
        unique_appels = []
        for appel in all_appels:
            appel_id = f"{appel.get('ref', '')}_{appel.get('numero', '')}_{appel.get('promoteur', '')}_{appel.get('objet', '')[:50]}".replace(' ', '_').replace('/', '_')
            if appel_id not in seen_ids:
                unique_appels.append(appel)
                seen_ids.add(appel_id)
        
        logger.info(f"Total unique: {len(unique_appels)} offres")
        return unique_appels
    
    def save_to_excel(self, appels_offres, filename=None):
        """Sauvegarde les données dans un fichier Excel avec onglet unique"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"appels_offres_TOUS_SECTEURS_{timestamp}.xlsx"
        
        if not appels_offres:
            logger.warning("Aucune donnée à sauvegarder")
            return filename
        
        # Préparer les données
        all_data = []
        
        for appel in appels_offres:
            row = {
                'PROMOTEUR': appel.get('promoteur', ''),
                'REF': appel.get('ref', ''),
                'LOCALISATION': appel.get('localisation', ''),
                'N°': appel.get('numero', ''),
                'DESCRIPTION': appel.get('objet', ''),
                'DATE_DEBUT': appel.get('date_debut', ''),
                'DATE LIMITE': appel.get('date_fin', ''),
                'CAHIER DE CHARGE': appel.get('asap', ''),
                'SOURCE': 'ARMP',
                'PAYS': 'Madagascar'
            }
            
            all_data.append(row)
        
        # Créer le fichier Excel
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Onglet principal
                if all_data:
                    df_all = pd.DataFrame(all_data)
                    df_all.to_excel(writer, index=False, sheet_name='Toutes_Offres')
                
                # Ajuster les colonnes
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_name = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 80)
                        worksheet.column_dimensions[column_name].width = adjusted_width
            
            logger.info(f"Fichier Excel sauvegardé: {filename}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde Excel: {e}")
        
        return filename
    
    def print_debug_info(self, html_content):
        """Affiche des informations de debug sur la structure HTML"""
        if not html_content:
            return
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        print(f"\n🔍 INFORMATIONS DE DEBUG:")
        print("-" * 50)
        print(f"Longueur du HTML: {len(html_content)} caractères")
        
        # Analyser les tables
        tables = soup.find_all('table')
        print(f"Nombre de tables: {len(tables)}")
        
        for i, table in enumerate(tables):
            print(f"\nTable {i+1}:")
            print(f"  - Classes: {table.get('class', [])}")
            print(f"  - ID: {table.get('id', 'Aucun')}")
            
            thead = table.find('thead')
            if thead:
                headers = thead.find_all(['th', 'td'])
                header_text = [h.get_text().strip() for h in headers]
                print(f"  - En-têtes: {header_text}")
            
            rows = table.find_all('tr')
            print(f"  - Nombre de lignes: {len(rows)}")
            
            if rows:
                first_row_cells = rows[0].find_all(['td', 'th'])
                print(f"  - Première ligne: {len(first_row_cells)} cellules")
                if first_row_cells:
                    first_cell_text = first_row_cells[0].get_text().strip()[:100]
                    print(f"  - Première cellule: {first_cell_text}...")
        
        # Chercher des liens PDF
        pdf_links = soup.find_all('a', href=lambda x: x and 'pdf' in x.lower())
        print(f"\nLiens PDF trouvés: {len(pdf_links)}")
    
    def print_summary(self, appels_offres):
        """Affiche un résumé détaillé des données extraites"""
        if not appels_offres:
            print("\n❌ AUCUN APPEL D'OFFRE TROUVÉ")
            print("\n💡 SUGGESTIONS DE DIAGNOSTIC:")
            print("   1. Vérifiez votre connexion internet")
            print("   2. Le site ARMP pourrait être en maintenance")
            print("   3. La structure HTML du site a peut-être changé")
            print("   4. Exécutez avec mode debug pour plus d'infos")
            return
        
        print(f"\n{'='*80}")
        print(f"🎯 RÉSUMÉ - EXTRACTION RÉUSSIE !")
        print(f"{'='*80}")
        print(f"📊 Total des offres extraites: {len(appels_offres)}")
        
        # Exemples
        print(f"\n📋 EXEMPLES D'OFFRES ({len(appels_offres)} total):")
        print("-" * 80)
        for appel in appels_offres[:5]:
            print(f"• PROMOTEUR: {appel.get('promoteur', 'N/A')[:40]}...")
            print(f"  REF: {appel.get('ref', 'N/A')} | Local: {appel.get('localisation', 'N/A')[:30]}... | N°: {appel.get('numero', 'N/A')}")
            print(f"  {appel.get('objet', 'N/A')[:70]}...")
        
        if len(appels_offres) > 5:
            print(f"   ... et {len(appels_offres) - 5} autres")


def main():
    """Fonction principale avec mode debug"""
    print("="*80)
    print("🎯 EXTRACTEUR ARMP - TOUS SECTEURS (Version Corrigée avec PROMOTEUR)")
    print("="*80)
    
    scraper = ARMPTableScraper()
    debug_mode = input("\n🔍 Activer le mode debug ? (y/N): ").lower().startswith('y')
    
    try:
        print(f"\n📡 1. Connexion au site ARMP...")
        
        # Test de connexion
        test_content = scraper.get_page_content(scraper.base_url)
        if debug_mode:
            scraper.print_debug_info(test_content)
        
        print(f"\n🔍 2. Extraction des appels d'offres...")
        appels_offres = scraper.scrape_all_pages()
        
        if not appels_offres:
            print(f"\n❌ Aucune offre trouvée.")
            if debug_mode:
                print("\n🔍 Mode debug - Analyse de la page:")
                scraper.print_debug_info(test_content)
            else:
                print("💡 Relancez avec le mode debug pour plus d'informations")
            return
        
        # Afficher le résumé
        print(f"\n📊 3. Résultats:")
        scraper.print_summary(appels_offres)
        
        # Sauvegarde
        print(f"\n💾 4. Sauvegarde...")
        excel_file = scraper.save_to_excel(appels_offres)
        
        print(f"\n✅ EXTRACTION TERMINÉE AVEC SUCCÈS !")
        print(f"📁 Fichier généré: {excel_file}")
        print(f"📋 Onglets créés:")
        print(f"   • Toutes_Offres: {len(appels_offres)} offres")
        
        print(f"\n🏢 CHAMP PROMOTEUR:")
        print("   • Extraction automatique des noms d'institutions/ministères")
        print("   • Affichage dans le résumé et Excel (colonne dédiée)")
        print("   • Patterns optimisés pour Ministère, Direction, Tribunal, etc.")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction: {e}")
        print(f"❌ Erreur: {e}")
        if debug_mode:
            import traceback
            print("\n🔍 Trace complète de l'erreur:")
            traceback.print_exc()


def run_in_colab():
    """Version optimisée pour Google Colab"""
    import sys
    
    # Installation des dépendances
    try:
        import requests, pandas as pd
        from bs4 import BeautifulSoup
    except ImportError:
        print("📦 Installation des dépendances...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "pandas", "beautifulsoup4", "openpyxl", "lxml"])
        import requests, pandas as pd
        from bs4 import BeautifulSoup
    
    print("🎯 DÉMARRAGE EXTRACTION ARMP (Google Colab) - TOUS SECTEURS AVEC PROMOTEUR")
    print("="*60)
    
    scraper = ARMPTableScraper()
    
    # Test de connexion
    print("📡 Test de connexion...")
    test_content = scraper.get_page_content(scraper.base_url)
    if test_content:
        print("✅ Connexion OK")
        scraper.print_debug_info(test_content)
    else:
        print("❌ Problème de connexion")
        return None, None
    
    # Extraction
    print("\n🔍 Extraction en cours...")
    appels_offres = scraper.scrape_all_pages()
    
    if appels_offres:
        # Résumé
        scraper.print_summary(appels_offres)
        
        # Sauvegarde
        excel_file = scraper.save_to_excel(appels_offres)
        
        # Créer DataFrame pour affichage
        display_data = []
        for appel in appels_offres:
            display_data.append({
                'PROMOTEUR': appel.get('promoteur', '')[:30] + '...' if len(appel.get('promoteur', '')) > 30 else appel.get('promoteur', ''),
                'REF': appel.get('ref', ''),
                'LOCALISATION': appel.get('localisation', '')[:30] + '...' if len(appel.get('localisation', '')) > 30 else appel.get('localisation', ''),
                'N°': appel.get('numero', ''),
                'DESCRIPTION': appel.get('objet', '')[:80] + '...' if len(appel.get('objet', '')) > 80 else appel.get('objet', ''),
                'DATE LIMITE': appel.get('date_fin', ''),
                'CAHIER DE CHARGE': 'Disponible' if appel.get('asap', '') != 'Non disponible' else 'Non',
                'SOURCE': 'ARMP',
                'PAYS': 'Madagascar'
            })
        
        df = pd.DataFrame(display_data)
        
        print(f"\n📋 APERÇU DES DONNÉES (avec PROMOTEUR):")
        print(df.to_string(index=False, max_colwidth=50))
        
        print(f"\n📁 Fichier Excel créé: {excel_file}")
        print("💡 Téléchargez le fichier avec:")
        print("   from google.colab import files")
        print(f"   files.download('{excel_file}')")
        
        return df, appels_offres
    else:
        print("❌ Aucune offre extraite")
        return None, None


def create_monitoring_script():
    """Crée un script de monitoring automatique"""
    monitoring_code = '''#!/usr/bin/env python3
"""
Script de Monitoring Automatique ARMP - TOUS SECTEURS AVEC PROMOTEUR
Vérifie les nouvelles offres toutes les heures
"""

import schedule
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class ARMPMonitor:
    def __init__(self, email_config=None):
        from armp_scraper import ARMPTableScraper  # Importer le scraper principal
        self.scraper = ARMPTableScraper()
        self.email_config = email_config
        
    def check_new_offers(self):
        """Vérifie les nouvelles offres"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\\n🔍 [{timestamp}] Vérification automatique...")
        
        try:
            appels_offres = self.scraper.scrape_all_pages()
            print(f"🆕 {len(appels_offres)} offres détectées !")
                
            # Sauvegarder
            filename = f"offres_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            self.scraper.save_to_excel(appels_offres, filename)
                
            # Envoyer notification email si configuré
            if self.email_config:
                self.send_email_notification(appels_offres)
                
            # Afficher un résumé
            for i, offre in enumerate(appels_offres[:5], 1):
                print(f"{i}. PROMOTEUR: {offre.get('promoteur', 'N/A')[:30]}...")
                print(f"   REF: {offre.get('ref', 'N/A')} | Local: {offre.get('localisation', 'N/A')[:30]}... | N°: {offre.get('numero', 'N/A')}")
                print(f"   {offre.get('objet', '')[:60]}...")
                
            if len(appels_offres) > 5:
                print(f"   ... et {len(appels_offres) - 5} autres")
                    
        except Exception as e:
            print(f"❌ Erreur lors de la vérification: {e}")
    
    def send_email_notification(self, nouvelles_offres):
        """Envoie une notification par email"""
        if not self.email_config:
            return
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['from']
            msg['To'] = self.email_config['to']
            msg['Subject'] = f"🆕 {len(nouvelles_offres)} nouvelles offres ARMP détectées"
            
            # Corps du message
            body = f"Nouvelles offres détectées le {datetime.now().strftime('%d/%m/%Y à %H:%M')}:\\n\\n"
            
            for i, offre in enumerate(nouvelles_offres, 1):
                body += f"{i}. PROMOTEUR: {offre.get('promoteur', '')}\\n"
                body += f"   REF: {offre.get('ref', '')} | Local: {offre.get('localisation', '')} | N°: {offre.get('numero', '')}\\n"
                body += f"   Objet: {offre.get('objet', '')}\\n"
                body += f"   Date limite: {offre.get('date_fin', 'N/A')}\\n"
                body += f"   Lien: {offre.get('asap', 'N/A')}\\n\\n"
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Envoyer
            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['username'], self.email_config['password'])
            server.send_message(msg)
            server.quit()
            
            print("📧 Notification email envoyée")
            
        except Exception as e:
            print(f"❌ Erreur envoi email: {e}")

def main():
    """Fonction principale du monitoring"""
    print("🤖 MONITORING AUTOMATIQUE ARMP - TOUS SECTEURS AVEC PROMOTEUR")
    print("="*50)
    
    # Configuration email optionnelle
    email_config = None
    setup_email = input("Configurer les notifications par email ? (y/N): ")
    
    if setup_email.lower().startswith('y'):
        email_config = {
            'from': input("Email expéditeur: "),
            'to': input("Email destinataire: "),
            'smtp_server': input("Serveur SMTP (ex: smtp.gmail.com): "),
            'smtp_port': int(input("Port SMTP (ex: 587): ") or "587"),
            'username': input("Nom d'utilisateur SMTP: "),
            'password': input("Mot de passe SMTP: ")
        }
    
    monitor = ARMPMonitor(email_config)
    
    # Première vérification immédiate
    print("\\n🚀 Première vérification...")
    monitor.check_new_offers()
    
    # Programmer les vérifications
    schedule.every(1).hours.do(monitor.check_new_offers)
    
    print("\\n⏰ Monitoring activé - vérification toutes les heures")
    print("⏹️  Appuyez sur Ctrl+C pour arrêter")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Vérifier chaque minute si une tâche doit s'exécuter
    except KeyboardInterrupt:
        print("\\n🛑 Monitoring arrêté")

if __name__ == "__main__":
    main()
'''
    
    with open('armp_monitor.py', 'w', encoding='utf-8') as f:
        f.write(monitoring_code)
    
    print("🤖 Script de monitoring créé: armp_monitor.py")
    print("\n💡 Pour l'utiliser:")
    print("   1. pip install schedule")
    print("   2. python armp_monitor.py")
    print("\n📧 Fonctionnalités du monitoring:")
    print("   • Vérification automatique toutes les heures")
    print("   • Sauvegarde des nouvelles offres uniquement")
    print("   • Notifications par email (optionnel)")
    print("   • Extraction du PROMOTEUR dans les notifications")
    print("   • Logs horodatés de toutes les vérifications")


def analyze_extracted_data(excel_file):
    """Analyse un fichier Excel déjà généré"""
    try:
        # Lire le fichier
        df = pd.read_excel(excel_file, sheet_name='Toutes_Offres')
        
        print(f"\n📊 ANALYSE DU FICHIER: {excel_file}")
        print("="*60)
        print(f"📋 Nombre total d'offres: {len(df)}")
        
        # Analyse des promoteurs
        if 'PROMOTEUR' in df.columns:
            top_promoteurs = df['PROMOTEUR'].value_counts().head(10)
            print(f"\n🏢 Top 10 des PROMOTEURS:")
            for promoteur, count in top_promoteurs.items():
                print(f"   {count}: {promoteur}")
        
        # Analyse des dates limites
        if 'DATE LIMITE' in df.columns:
            dates_definies = df['DATE LIMITE'].notna().sum()
            print(f"\n📅 Offres avec date limite définie: {dates_definies}/{len(df)}")
        
        # Top 5 des références
        if 'REF' in df.columns:
            top_refs = df['REF'].value_counts().head()
            print(f"\n🏢 Top 5 des références:")
            for ref, count in top_refs.items():
                print(f"   {count}: {ref}")
        
        # Analyse des localisations
        if 'LOCALISATION' in df.columns:
            top_loc = df['LOCALISATION'].value_counts().head()
            print(f"\n📍 Top 5 des localisations:")
            for loc, count in top_loc.items():
                print(f"   {count}: {loc}")
        
        return df
        
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse: {e}")
        return None


# Ancien bloc main() commenté pour permettre à Flask de démarrer
# if __name__ == "__main__":
#     main()


# ================================================================================
# GUIDE D'UTILISATION COMPLET - VERSION TOUS SECTEURS AVEC PROMOTEUR
# ================================================================================
"""
🎯 EXTRACTEUR ARMP - VERSION CORRIGÉE POUR TOUS SECTEURS + PROMOTEUR

🆕 MODIFICATIONS:
   • Suppression du filtrage par secteur (informatique/textile)
   • Extraction de TOUTES les offres d'appels publics
   • Mots-clés supprimés (plus de filtrage)
   • Onglet unique 'Toutes_Offres' dans Excel
   • Titres et résumés mis à jour pour "Tous Secteurs"

🔧 UTILISATION:

1. 📱 UTILISATION NORMALE:
   python armp_scraper.py

2. 🔬 AVEC MODE DEBUG:
   Répondre "y" quand demandé pour voir la structure HTML

3. 📊 GOOGLE COLAB:
   df, data = run_in_colab()

5. 🤖 MONITORING AUTOMATIQUE:
   create_monitoring_script()  # Crée armp_monitor.py
   pip install schedule
   python armp_monitor.py

6. 📈 ANALYSER UN FICHIER EXISTANT:
   analyze_extracted_data('appels_offres_TOUS_SECTEURS_20231216_143022.xlsx')

🆕 FONCTIONNALITÉS PROMOTEUR (inchangées):

📋 EXTRACTION INTELLIGENTE:
• Patterns regex pour Ministère de la Justice, Direction Régionale, etc.
• Fallback automatique sur le début du texte d'entité
• Nettoyage et capitalisation automatique
• Évite les faux positifs (références numériques)

📊 ANALYSE PAR PROMOTEUR:
• Top 10 des promoteurs les plus actifs
• Filtrage possible par promoteur
• Statistiques dans analyze_extracted_data()

📧 NOTIFICATIONS AMÉLIORÉES:
• Affichage du promoteur dans les emails
• Meilleure identification de l'origine des offres

📋 COLONNES EXTRAITES (STRUCTURE SIMPLIFIÉE):

• PROMOTEUR: Nom de l'institution/organisme (ex: "Ministère De La Justice")
• REF: Référence extraite
• LOCALISATION: Lieu/localisation extraite
• N°: Numéro extraite (complet)
• DESCRIPTION: Description complète de l'appel d'offres
• DATE_DEBUT: Période de validité (si détectée)
• DATE LIMITE: Date limite
• CAHIER DE CHARGE: URL vers le document PDF
• SOURCE: ARMP
• PAYS: Madagascar

🔍 EXEMPLES D'EXTRACTION PROMOTEUR (inchangés):

ENTRÉE: "MINISTERE DE LA JUSTICE - Ref: 04-CONV/TPMVO/PRM/611/25"
→ PROMOTEUR: "Ministère De La Justice"

ENTRÉE: "PAOSTRA MALAGASY - Ref: 25/16-PAOSTRA/DGPRM/ACO"
→ PROMOTEUR: "Paostra Malagasy"

ENTRÉE: "DIRECTION REGIONALE DES MINES VATOMANDRY"
→ PROMOTEUR: "Direction Régionale Des Mines Vatomandry"

⚠️ DÉPENDANCES (inchangées):

pip install requests pandas beautifulsoup4 openpyxl lxml

Pour le monitoring:
pip install schedule

✨ Cette version extrait TOUTES les offres sans filtrage par secteur,
   tout en conservant l'extraction intelligente du PROMOTEUR.
   Le champ PROMOTEUR est disponible dans:
   • L'onglet Excel 'Toutes_Offres' (colonne en 1ère position)
   • Le résumé d'extraction
   • Les notifications email du monitoring
   • L'analyse des fichiers existants
   • Les affichages debug et Colab

📈 BÉNÉFICES:
• Extraction complète de toutes les données
• Meilleure identification des acheteurs publics via PROMOTEUR
• Statistiques par promoteur (Top 10 automatique)
• Notifications plus informatives
• Meilleure organisation des données
"""

# ================================================================================
# FLASK API + POSTGRESQL SUPPORT
# ================================================================================

from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import threading
from urllib.parse import urlparse

app = Flask(__name__)
CORS(app)

# PostgreSQL configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'tender_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

def get_db_connection():
    """Create and return a PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

def insert_tender(tender_data):
    """Insert a tender into PostgreSQL database"""
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenders_armp (
                id SERIAL PRIMARY KEY,
                reference VARCHAR(255),
                description TEXT,
                publication_date VARCHAR(100),
                expiration_date VARCHAR(100),
                promoter VARCHAR(500),
                external_url TEXT,
                region VARCHAR(255),
                numero VARCHAR(255),
                date_info TEXT,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert tender
        cursor.execute("""
            INSERT INTO tenders_armp
            (reference, description, publication_date, expiration_date, promoter, external_url, region, numero, date_info, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            tender_data.get('ref', ''),
            tender_data.get('objet', ''),
            tender_data.get('date_debut', ''),
            tender_data.get('date_fin', ''),
            tender_data.get('promoteur', ''),
            tender_data.get('asap', ''),
            tender_data.get('localisation', ''),
            tender_data.get('numero', ''),
            tender_data.get('date_info', ''),
            'pending'
        ))

        tender_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Tender inserted with ID: {tender_id}")
        return True

    except Exception as e:
        logger.error(f"Error inserting tender: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

def get_all_tenders(status=None):
    """Get all tenders from database, optionally filtered by status"""
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        if status:
            cursor.execute("""
                SELECT * FROM tenders_armp
                WHERE status = %s
                ORDER BY created_at DESC
            """, (status,))
        else:
            cursor.execute("""
                SELECT * FROM tenders_armp
                ORDER BY created_at DESC
            """)

        tenders = cursor.fetchall()
        cursor.close()
        conn.close()

        return [dict(tender) for tender in tenders]

    except Exception as e:
        logger.error(f"Error fetching tenders: {e}")
        if conn:
            conn.close()
        return []

def count_tenders(status=None):
    """Count tenders in database, optionally filtered by status"""
    conn = get_db_connection()
    if not conn:
        return 0

    try:
        cursor = conn.cursor()

        if status:
            cursor.execute("SELECT COUNT(*) FROM tenders_armp WHERE status = %s", (status,))
        else:
            cursor.execute("SELECT COUNT(*) FROM tenders_armp")

        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        return count

    except Exception as e:
        logger.error(f"Error counting tenders: {e}")
        if conn:
            conn.close()
        return 0

# Flask Routes

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint with tender counts"""
    try:
        pending_count = count_tenders('pending')
        validated_count = count_tenders('active')

        return jsonify({
            'status': 'ok',
            'service': 'armp-scraper',
            'pending_count': pending_count,
            'validated_count': validated_count
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/status', methods=['GET'])
def status():
    """Status endpoint (same as health)"""
    return health()

@app.route('/api/pending', methods=['GET'])
def get_pending():
    """Get all pending tenders"""
    try:
        limit = request.args.get('limit', type=int, default=10)
        tenders = get_all_tenders('pending')

        # Return structured format matching other scrapers (TUNEPS AO, etc.)
        return jsonify({
            'success': True,
            'offres': tenders,
            'count': len(tenders),
            'limit': limit
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'offres': [],
            'count': 0
        }), 500

@app.route('/api/pending-all', methods=['GET'])
def get_pending_all():
    """Get all pending tenders (same as /api/pending)"""
    return get_pending()

@app.route('/api/tenders', methods=['GET'])
def get_tenders():
    """Get all validated (active) tenders"""
    try:
        limit = request.args.get('limit', type=int, default=10)
        tenders = get_all_tenders('active')

        # Return structured format matching other scrapers
        return jsonify({
            'success': True,
            'offres': tenders,
            'count': len(tenders),
            'limit': limit
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'offres': [],
            'count': 0
        }), 500

@app.route('/api/validated', methods=['GET'])
def get_validated():
    """Get all validated tenders (same as /api/tenders)"""
    return get_tenders()

@app.route('/api/scrape', methods=['POST'])
def scrape():
    """Launch scraping in background thread and save to PostgreSQL"""
    def scrape_task():
        try:
            print("🚀 [ARMP] Starting ARMP scraping task...")
            logger.info("Starting ARMP scraping task...")
            scraper = ARMPTableScraper()
            tenders = scraper.scrape_all_pages()

            if tenders:
                print(f"✅ [ARMP] Found {len(tenders)} tenders from ARMP website")
                logger.info(f"Found {len(tenders)} tenders")
                success_count = 0

                for tender in tenders:
                    if insert_tender(tender):
                        success_count += 1

                print(f"💾 [ARMP] Successfully inserted {success_count}/{len(tenders)} tenders into PostgreSQL")
                logger.info(f"Successfully inserted {success_count}/{len(tenders)} tenders")
            else:
                print("⚠️ [ARMP] No tenders found during scraping - site may be empty or structure changed")
                logger.warning("No tenders found during scraping")

        except Exception as e:
            print(f"❌ [ARMP] Error in scraping task: {e}")
            logger.error(f"Error in scraping task: {e}")

    # Start scraping in background thread
    thread = threading.Thread(target=scrape_task)
    thread.daemon = True
    thread.start()

    return jsonify({
        'message': 'Scraping started in background',
        'status': 'running'
    }), 202

@app.route('/api/validate/<reference>', methods=['POST'])
def validate_tender(reference):
    """Mark a tender as active (validated)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({
            'error': 'Database connection failed'
        }), 500

    try:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE tenders_armp
            SET status = 'active', updated_at = CURRENT_TIMESTAMP
            WHERE reference = %s
            RETURNING id
        """, (reference,))

        result = cursor.fetchone()

        if result:
            conn.commit()
            cursor.close()
            conn.close()

            return jsonify({
                'message': 'Tender validated successfully',
                'reference': reference
            }), 200
        else:
            cursor.close()
            conn.close()

            return jsonify({
                'error': 'Tender not found'
            }), 404

    except Exception as e:
        logger.error(f"Error validating tender: {e}")
        if conn:
            conn.rollback()
            conn.close()

        return jsonify({
            'error': str(e)
        }), 500

if __name__ == "__main__":
    logger.info("Starting ARMP Flask API on port 5007...")
    app.run(host='0.0.0.0', port=5007, debug=True)