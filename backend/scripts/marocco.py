import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template_string, request, jsonify
import logging
from typing import Dict, List
from datetime import datetime
import json

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class MarchesPublicsExtractor:
    """Extracteur optimisé pour marchespublics.gov.tn utilisant requests"""
    
    BASE_URL = "https://www.marchespublics.gov.tn"
    SEARCH_URL = f"{BASE_URL}/app/protected/form.jsf"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
        })

    def extract(self, search_params: Dict, max_pages: int = 3) -> Dict:
        """
        Extraction principale avec requests (méthode la plus fiable)
        
        Args:
            search_params: Paramètres de recherche
            max_pages: Nombre maximum de pages à extraire
        """
        logger.info("🚀 Début de l'extraction...")
        logger.info("🔧 Méthode: requests (HTTP direct)")
        
        all_results = []
        stats = {
            'total_results': 0,
            'pages_extracted': 0,
            'method': 'requests',
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            for page in range(1, max_pages + 1):
                logger.info(f"📄 Traitement page {page}/{max_pages}")
                
                results = self._extract_page_requests(page, search_params)
                
                if not results:
                    logger.warning(f"⚠️ Aucun résultat page {page}")
                    break
                
                all_results.extend(results)
                stats['pages_extracted'] = page
                stats['total_results'] = len(all_results)
                
                logger.info(f"✅ Page {page}: {len(results)} marchés extraits")
            
            logger.info(f"🎉 Extraction terminée: {stats['total_results']} marchés")
            
            return {
                'success': True,
                'data': all_results,
                'stats': stats
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur extraction: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data': all_results,
                'stats': stats
            }

    def _extract_page_requests(self, page: int, params: Dict) -> List[Dict]:
        """Extraction d'une page via requests"""
        try:
            # Construction URL avec paramètres
            search_url = self._build_search_url(page, params)
            
            # Requête HTTP
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
            
            # Parsing HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extraction des marchés
            results = self._parse_marches(soup)
            
            return results
            
        except requests.RequestException as e:
            logger.error(f"❌ Erreur requête page {page}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"❌ Erreur parsing page {page}: {str(e)}")
            return []

    def _build_search_url(self, page: int, params: Dict) -> str:
        """Construction de l'URL de recherche"""
        base = self.SEARCH_URL
        
        # Paramètres par défaut
        query_params = {
            'page': page,
            'type': params.get('type', 'tous'),
            'secteur': params.get('secteur', ''),
            'region': params.get('region', ''),
            'statut': params.get('statut', 'en_cours')
        }
        
        # Construction query string
        query_string = '&'.join(f"{k}={v}" for k, v in query_params.items() if v)
        
        return f"{base}?{query_string}" if query_string else base

    def _parse_marches(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse les marchés depuis le HTML"""
        marches = []
        
        # Recherche des conteneurs de marchés (à adapter selon la structure réelle)
        containers = soup.find_all(['div', 'tr'], class_=lambda x: x and any(
            keyword in str(x).lower() for keyword in ['marche', 'appel', 'offre', 'consultation']
        ))
        
        if not containers:
            # Tentative avec table rows
            containers = soup.find_all('tr')[1:]  # Skip header
        
        for idx, container in enumerate(containers):
            try:
                marche = self._parse_marche_item(container, idx)
                if marche:
                    marches.append(marche)
            except Exception as e:
                logger.debug(f"⚠️ Erreur parsing item {idx}: {str(e)}")
                continue
        
        return marches

    def _parse_marche_item(self, element, idx: int) -> Dict:
        """Parse un élément de marché individuel"""
        # Extraction texte
        text = element.get_text(separator=' ', strip=True)
        
        if not text or len(text) < 20:
            return None
        
        # Extraction des liens
        links = element.find_all('a', href=True)
        detail_url = None
        if links:
            href = links[0]['href']
            detail_url = href if href.startswith('http') else f"{self.BASE_URL}{href}"
        
        # Extraction données structurées
        cells = element.find_all(['td', 'div'])
        
        marche = {
            'id': f"marche_{idx}_{datetime.now().timestamp()}",
            'titre': self._extract_titre(element),
            'reference': self._extract_reference(element),
            'organisme': self._extract_organisme(element),
            'type': self._extract_type(element),
            'secteur': self._extract_secteur(element),
            'montant': self._extract_montant(element),
            'date_publication': self._extract_date(element, 'publication'),
            'date_limite': self._extract_date(element, 'limite'),
            'statut': self._extract_statut(element),
            'detail_url': detail_url,
            'description': text[:500],
            'extracted_at': datetime.now().isoformat()
        }
        
        return marche

    def _extract_titre(self, elem) -> str:
        """Extrait le titre du marché"""
        # Recherche titre dans balises courantes
        for tag in ['h3', 'h4', 'h5', 'strong', 'b']:
            title_elem = elem.find(tag)
            if title_elem:
                return title_elem.get_text(strip=True)
        
        # Fallback: premier lien ou texte long
        link = elem.find('a')
        if link:
            return link.get_text(strip=True)
        
        text = elem.get_text(strip=True)
        return text.split('.')[0][:200] if text else "Titre non disponible"

    def _extract_reference(self, elem) -> str:
        """Extrait la référence"""
        text = elem.get_text()
        # Patterns courants: REF, N°, AO, etc.
        import re
        patterns = [
            r'(?:REF|Réf|N°|AO|AP)[\s:]*([A-Z0-9/-]+)',
            r'\b([A-Z]{2,}\d{2,}[/-]?\d*)\b'
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return "N/A"

    def _extract_organisme(self, elem) -> str:
        """Extrait l'organisme"""
        text = elem.get_text()
        # Recherche mots-clés
        keywords = ['ministère', 'direction', 'société', 'office', 'agence']
        lines = text.split('\n')
        for line in lines:
            if any(kw in line.lower() for kw in keywords):
                return line.strip()[:200]
        return "Organisme non spécifié"

    def _extract_type(self, elem) -> str:
        """Extrait le type de marché"""
        text = elem.get_text().lower()
        types = {
            'appel d\'offres': ['appel d\'offres', 'ao', 'appel offre'],
            'consultation': ['consultation', 'consul'],
            'marché négocié': ['marché négocié', 'gré à gré'],
            'concours': ['concours'],
        }
        for marche_type, keywords in types.items():
            if any(kw in text for kw in keywords):
                return marche_type
        return "Non spécifié"

    def _extract_secteur(self, elem) -> str:
        """Extrait le secteur"""
        text = elem.get_text().lower()
        secteurs = {
            'travaux': ['travaux', 'construction', 'bâtiment'],
            'fournitures': ['fourniture', 'équipement', 'matériel'],
            'services': ['service', 'prestation', 'étude'],
        }
        for secteur, keywords in secteurs.items():
            if any(kw in text for kw in keywords):
                return secteur
        return "Non spécifié"

    def _extract_montant(self, elem) -> str:
        """Extrait le montant"""
        import re
        text = elem.get_text()
        # Patterns monétaires
        patterns = [
            r'([\d\s]+(?:\.\d+)?)\s*(?:TND|DT|dinars?)',
            r'montant[:\s]*([\d\s]+(?:\.\d+)?)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip() + " TND"
        return "Non communiqué"

    def _extract_date(self, elem, date_type: str) -> str:
        """Extrait une date (publication ou limite)"""
        import re
        text = elem.get_text()
        
        # Patterns de dates
        date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b'
        matches = re.findall(date_pattern, text)
        
        if matches:
            # Publication = première date, Limite = dernière date
            return matches[0] if date_type == 'publication' else matches[-1]
        
        return "Non spécifiée"

    def _extract_statut(self, elem) -> str:
        """Extrait le statut"""
        text = elem.get_text().lower()
        if 'clôturé' in text or 'clos' in text:
            return "Clôturé"
        elif 'en cours' in text or 'ouvert' in text:
            return "En cours"
        elif 'annulé' in text:
            return "Annulé"
        return "En cours"  # Par défaut


# Interface Web Flask
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Extracteur Marchés Publics Tunisie</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        .header p {
            opacity: 0.95;
            font-size: 1.1em;
        }
        .content {
            padding: 30px;
        }
        .search-form {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .form-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }
        .form-group {
            display: flex;
            flex-direction: column;
        }
        .form-group label {
            font-weight: 600;
            margin-bottom: 5px;
            color: #333;
        }
        .form-group input,
        .form-group select {
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
            transition: all 0.3s;
        }
        .form-group input:focus,
        .form-group select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .btn {
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        .btn-primary:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 30px;
        }
        .loading.active {
            display: block;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-card .value {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .stat-card .label {
            opacity: 0.9;
        }
        .results {
            display: none;
        }
        .results.active {
            display: block;
        }
        .marche-card {
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            transition: all 0.3s;
        }
        .marche-card:hover {
            border-color: #667eea;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }
        .marche-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 15px;
        }
        .marche-title {
            font-size: 1.3em;
            font-weight: 600;
            color: #333;
            flex: 1;
        }
        .marche-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            margin-left: 15px;
        }
        .badge-en-cours {
            background: #d4edda;
            color: #155724;
        }
        .badge-cloture {
            background: #f8d7da;
            color: #721c24;
        }
        .marche-info {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 10px;
            margin-bottom: 15px;
        }
        .info-item {
            display: flex;
            align-items: center;
        }
        .info-label {
            font-weight: 600;
            color: #666;
            margin-right: 8px;
        }
        .info-value {
            color: #333;
        }
        .marche-actions {
            display: flex;
            gap: 10px;
        }
        .btn-sm {
            padding: 8px 15px;
            font-size: 14px;
        }
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        .btn-secondary:hover {
            background: #5a6268;
        }
        .export-section {
            margin-top: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            text-align: center;
        }
        .alert {
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏛️ Extracteur Marchés Publics</h1>
            <p>Système d'extraction automatique des marchés publics tunisiens</p>
            <p style="font-size: 0.9em; margin-top: 10px;">✅ Méthode optimisée: HTTP Direct (requests)</p>
        </div>

        <div class="content">
            <div class="search-form">
                <h2 style="margin-bottom: 20px;">🔍 Paramètres de recherche</h2>
                <form id="searchForm">
                    <div class="form-row">
                        <div class="form-group">
                            <label>Type de marché</label>
                            <select name="type">
                                <option value="tous">Tous types</option>
                                <option value="appel_offres">Appels d'offres</option>
                                <option value="consultation">Consultations</option>
                                <option value="marche_negocie">Marchés négociés</option>
                            </select>
                        </div>

                        <div class="form-group">
                            <label>Secteur</label>
                            <select name="secteur">
                                <option value="">Tous secteurs</option>
                                <option value="travaux">Travaux</option>
                                <option value="fournitures">Fournitures</option>
                                <option value="services">Services</option>
                            </select>
                        </div>

                        <div class="form-group">
                            <label>Région</label>
                            <select name="region">
                                <option value="">Toutes régions</option>
                                <option value="tunis">Tunis</option>
                                <option value="ariana">Ariana</option>
                                <option value="sousse">Sousse</option>
                                <option value="sfax">Sfax</option>
                            </select>
                        </div>

                        <div class="form-group">
                            <label>Nombre de pages</label>
                            <input type="number" name="max_pages" value="3" min="1" max="10">
                        </div>
                    </div>

                    <div style="text-align: center; margin-top: 20px;">
                        <button type="submit" class="btn btn-primary" id="extractBtn">
                            🚀 Lancer l'extraction
                        </button>
                    </div>
                </form>
            </div>

            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p style="font-size: 1.2em; color: #666;">Extraction en cours...</p>
                <p style="color: #999; margin-top: 10px;">Méthode: HTTP Direct (requests)</p>
            </div>

            <div id="alert"></div>

            <div class="results" id="results">
                <div class="stats" id="stats"></div>
                <div id="marchesList"></div>
                <div class="export-section">
                    <button class="btn btn-secondary" onclick="exportToJSON()">
                        📥 Exporter en JSON
                    </button>
                    <button class="btn btn-secondary" onclick="exportToCSV()">
                        📊 Exporter en CSV
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let extractedData = [];

        document.getElementById('searchForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const params = Object.fromEntries(formData.entries());
            
            document.getElementById('extractBtn').disabled = true;
            document.getElementById('loading').classList.add('active');
            document.getElementById('results').classList.remove('active');
            document.getElementById('alert').innerHTML = '';
            
            try {
                const response = await fetch('/scrape', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(params)
                });
                
                const data = await response.json();
                
                if (data.success) {
                    extractedData = data.data;
                    displayResults(data);
                    showAlert('success', `✅ Extraction réussie: ${data.stats.total_results} marchés extraits`);
                } else {
                    showAlert('error', `❌ Erreur: ${data.error}`);
                }
            } catch (error) {
                showAlert('error', `❌ Erreur réseau: ${error.message}`);
            } finally {
                document.getElementById('extractBtn').disabled = false;
                document.getElementById('loading').classList.remove('active');
            }
        });

        function displayResults(data) {
            const stats = data.stats;
            const marches = data.data;
            
            document.getElementById('stats').innerHTML = `
                <div class="stat-card">
                    <div class="value">${stats.total_results}</div>
                    <div class="label">Marchés extraits</div>
                </div>
                <div class="stat-card">
                    <div class="value">${stats.pages_extracted}</div>
                    <div class="label">Pages traitées</div>
                </div>
                <div class="stat-card">
                    <div class="value">${stats.method}</div>
                    <div class="label">Méthode utilisée</div>
                </div>
            `;
            
            const marchesList = document.getElementById('marchesList');
            marchesList.innerHTML = marches.map(marche => `
                <div class="marche-card">
                    <div class="marche-header">
                        <div class="marche-title">${marche.titre}</div>
                        <span class="marche-badge badge-${marche.statut.toLowerCase().replace(' ', '-')}">
                            ${marche.statut}
                        </span>
                    </div>
                    
                    <div class="marche-info">
                        <div class="info-item">
                            <span class="info-label">📋 Référence:</span>
                            <span class="info-value">${marche.reference}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">🏢 Organisme:</span>
                            <span class="info-value">${marche.organisme}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">📂 Type:</span>
                            <span class="info-value">${marche.type}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">🔧 Secteur:</span>
                            <span class="info-value">${marche.secteur}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">💰 Montant:</span>
                            <span class="info-value">${marche.montant}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">📅 Publication:</span>
                            <span class="info-value">${marche.date_publication}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">⏰ Date limite:</span>
                            <span class="info-value">${marche.date_limite}</span>
                        </div>
                    </div>
                    
                    ${marche.detail_url ? `
                        <div class="marche-actions">
                            <a href="${marche.detail_url}" target="_blank" class="btn btn-secondary btn-sm">
                                🔗 Voir détails
                            </a>
                        </div>
                    ` : ''}
                </div>
            `).join('');
            
            document.getElementById('results').classList.add('active');
        }

        function showAlert(type, message) {
            const alert = document.getElementById('alert');
            alert.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
            setTimeout(() => { alert.innerHTML = ''; }, 5000);
        }

        function exportToJSON() {
            const dataStr = JSON.stringify(extractedData, null, 2);
            const blob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `marches_publics_${new Date().toISOString()}.json`;
            a.click();
        }

        function exportToCSV() {
            if (extractedData.length === 0) return;
            
            const headers = Object.keys(extractedData[0]);
            const csvContent = [
                headers.join(','),
                ...extractedData.map(row => 
                    headers.map(h => `"${(row[h] || '').toString().replace(/"/g, '""')}"`).join(',')
                )
            ].join('\\n');
            
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `marches_publics_${new Date().toISOString()}.csv`;
            a.click();
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/scrape', methods=['POST'])
def scrape():
    try:
        params = request.get_json()
        max_pages = int(params.get('max_pages', 3))
        
        extractor = MarchesPublicsExtractor()
        result = extractor.extract(params, max_pages)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Erreur endpoint /scrape: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': [],
            'stats': {'total_results': 0, 'pages_extracted': 0}
        })

if __name__ == '__main__':
    logger.info("🚀 Démarrage du serveur Flask...")
    logger.info("📡 Méthode par défaut: requests (HTTP Direct)")
    logger.info("🌐 Interface disponible sur: http://127.0.0.1:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)