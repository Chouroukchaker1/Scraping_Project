import os
import json
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify, request, send_file
from flask_cors import CORS
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
from dotenv import load_dotenv
import pdfplumber
import traceback
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict

# Charger variables d'environnement
load_dotenv()

# Configuration API appeloffres.net
API_BASE_URL = os.getenv("API_BASE_URL", "https://be.appeloffres.net/api")
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login/"
TENDER_ENDPOINT = f"{API_BASE_URL}/tender"
PROMOTER_ENDPOINT = f"{API_BASE_URL}/promoter"
EMAIL = os.getenv("API_EMAIL", "oumayma.dahmani@tunipages.tn")
PASSWORD = os.getenv("API_PASSWORD", "Ah0F553KKu0A")
DEFAULT_SOURCE_ID = os.getenv("DEFAULT_SOURCE_ID", "1760")
DEFAULT_PROMOTER_ID = os.getenv("DEFAULT_PROMOTER_ID", "223472")
DEFAULT_AVIS_ID = os.getenv("DEFAULT_AVIS_ID", "1")
DEFAULT_PAYS_ID = os.getenv("DEFAULT_PAYS_ID", "70")

# Dossiers
PDF_DIR = "giz_documents"
for directory in [PDF_DIR]:
    os.makedirs(directory, exist_ok=True)

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('giz_scraper.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class GIZTender:
    date_publication: str = ""
    date_limite: str = ""
    description: str = ""
    type: str = ""
    autorite: str = ""
    reference: str = ""
    pays: str = ""
    source: str = "GIZ"
    project_id: str = ""
    lien_details: str = ""
    pdf_links: List[str] = field(default_factory=list)
    lots: List[str] = field(default_factory=list)
    cahier_charges: Dict = field(default_factory=dict)
    details_complets: Dict = field(default_factory=dict)
    secteur_activite: str = ""
    secteur_activite_id: Optional[int] = None
    activities_ids: List[int] = field(default_factory=list)

class GIZScraper:
    def __init__(self):
        self.base_url = "https://ausschreibungen.giz.de"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        })
        self.access_token = None
        self.promoter_cache = {}
        self.tenders_cache = []
        self.pdf_dir = PDF_DIR

        self.pays_list = [
            'Ouzbékistan', 'Usbekistan', 'Uzbekistan', 'Afghanistan', 'Allemagne',
            'Albania', 'Algérie', 'Arménie', 'Azerbaïdjan', 'Bangladesh', 'Biélorussie',
            'Bénin', 'Bosnie-Herzégovine', 'Botswana', 'Brésil', 'Burkina Faso',
            'Burundi', 'Cambodge', 'Cameroun', 'Chine', 'Colombie', "Côte d'Ivoire",
            'Égypte', 'Éthiopie', 'Géorgie', 'Ghana', 'Guatemala', 'Guinée', 'Haïti',
            'Inde', 'Indonésie', 'Irak', 'Jordanie', 'Kazakhstan', 'Kenya', 'Kirghizistan',
            'Kosovo', 'Laos', 'Liban', 'Liberia', 'Madagascar', 'Malawi', 'Mali',
            'Maroc', 'Mauritanie', 'Mexique', 'Moldavie', 'Mongolie', 'Mozambique',
            'Myanmar', 'Namibie', 'Népal', 'Nicaragua', 'Niger', 'Nigeria', 'Ouganda',
            'Pakistan', 'Palestine', 'Pérou', 'Philippines', 'Rwanda', 'Sénégal',
            'Serbie', 'Somalie', 'Soudan', 'Soudan du Sud', 'Sri Lanka', 'Syrie',
            'Tadjikistan', 'Tanzanie', 'Thaïlande', 'Timor oriental', 'Togo', 'Tunisie',
            'Turquie', 'Turkménistan', 'Ukraine', 'Uruguay', 'Vietnam', 'Yémen',
            'Zambie', 'Zimbabwe'
        ]

    def extract_project_id_from_js(self, js_string):
        if not js_string:
            return None
        match = re.search(r"pid=([A-Z0-9]+)", js_string)
        return match.group(1) if match else None

    def get_tenders_in_range(self, date_debut, date_fin):
        url = f"{self.base_url}/Satellite/company/welcome.do"
        try:
            logger.info(f"Connexion à: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            table = soup.find('table', class_='csx-new-table') or soup.find('table')
            if not table:
                logger.error("Tableau non trouvé")
                return []

            tenders = []
            date_debut_obj = datetime.strptime(date_debut, "%Y-%m-%d")
            date_fin_obj = datetime.strptime(date_fin, "%Y-%m-%d")
            rows = table.find_all('tr')

            for row in rows[1:]:
                cols = row.find_all('td')
                if len(cols) < 3:
                    continue

                date_pub_str = cols[0].get_text(strip=True)
                try:
                    date_pub_obj = datetime.strptime(date_pub_str, "%d.%m.%Y")
                    if not (date_debut_obj <= date_pub_obj <= date_fin_obj):
                        continue
                except ValueError:
                    continue

                date_limite = cols[1].get_text(strip=True)
                description = cols[2].get_text(strip=True)
                type_ao = cols[3].get_text(strip=True) if len(cols) > 3 else ""
                autorite = cols[4].get_text(strip=True) if len(cols) > 4 else ""

                reference = re.match(r'(\d{8})', description).group(1) if re.match(r'(\d{8})', description) else ""

                tender = GIZTender(
                    date_publication=date_pub_str,
                    date_limite=date_limite,
                    description=description,
                    type=type_ao,
                    autorite=autorite,
                    reference=reference
                )

                # Extraire lien
                link_elem = cols[2].find('a')
                if link_elem:
                    onclick = link_elem.get('onclick', '')
                    href = link_elem.get('href', '')
                    js_call = onclick if onclick else href
                    pid = self.extract_project_id_from_js(js_call)
                    if pid:
                        tender.project_id = pid
                        tender.lien_details = f"{self.base_url}/Satellite/public/company/projectForwarding.do?pid={pid}"

                if 'informatique' in description.lower():
                    tender.secteur_activite = "Technologies de l'Information"
                elif 'textile' in description.lower() or 'cuir' in description.lower():
                    tender.secteur_activite = "Cuir et Habillement"
                else:
                    tender.secteur_activite = "Bâtiment"

                tenders.append(tender)

            return tenders

        except Exception as e:
            logger.error(f"Erreur scraping: {e}")
            traceback.print_exc()
            return []

    def get_project_details(self, tender):
        if not tender.lien_details:
            return tender
        try:
            response = self.session.get(tender.lien_details, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            content = soup.find('div', id='content') or soup.body

            if content:
                if not tender.reference:
                    ref_text = content.get_text()
                    match = re.search(r'(\d{8})', ref_text)
                    if match:
                        tender.reference = match.group(1)

                full_text = content.get_text().lower()
                for pays in self.pays_list:
                    if pays.lower() in full_text:
                        tender.pays = pays
                        break

                for link in content.find_all('a', href=True):
                    if '.pdf' in link['href'].lower():
                        pdf_url = urljoin(tender.lien_details, link['href'])
                        if pdf_url not in tender.pdf_links:
                            tender.pdf_links.append(pdf_url)

            return tender
        except Exception as e:
            logger.error(f"Erreur détails: {e}")
            return tender

    def download_document(self, url, filename):
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            filepath = os.path.join(self.pdf_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            logger.info(f"Téléchargé: {filename}")
            return filepath
        except Exception as e:
            logger.error(f"Erreur téléchargement: {e}")
            return None

    def extract_from_pdf(self, pdf_path, tender):
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = "".join(page.extract_text() or "" for page in pdf.pages)
                if not tender.reference:
                    match = re.search(r'(\d{8})', text)
                    if match:
                        tender.reference = match.group(1)
                if not tender.pays:
                    text_lower = text.lower()
                    for pays in self.pays_list:
                        if pays.lower() in text_lower:
                            tender.pays = pays
                            break
                lots = re.findall(r'(Lot\s+\d+|Lot\s+[A-Z]+|Tranche\s+\d+)', text, re.IGNORECASE)
                if lots:
                    tender.lots = list(set(lots))
        except Exception as e:
            logger.error(f"Erreur PDF: {e}")

    def login_appeloffres(self):
        if self.access_token:
            return True
        try:
            response = requests.post(LOGIN_ENDPOINT, json={"email": EMAIL, "password": PASSWORD}, timeout=30)
            if response.status_code in [200, 201]:
                self.access_token = response.json().get("accessToken")
                logger.info("Connexion API OK")
                return True
            logger.error(f"Échec login: {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Erreur login: {e}")
            return False

    def get_or_create_promoter(self, name):
        if not name:
            return DEFAULT_PROMOTER_ID
        key = name.strip().lower()
        if key in self.promoter_cache:
            return self.promoter_cache[key]
        if not self.login_appeloffres():
            return DEFAULT_PROMOTER_ID
        payload = {
            "name": name, "description": f"GIZ: {name}", "companyName": name,
            "reference": re.sub(r'\W+', '_', name.upper())[:20], "isEnabled": True,
            "address": {"street": "N/A", "city": "N/A", "country": "N/A", "postalCode": "N/A"}
        }
        try:
            response = requests.post(PROMOTER_ENDPOINT, json=payload,
                                   headers={"Authorization": f"Bearer {self.access_token}"}, timeout=30)
            if response.status_code in [200, 201]:
                pid = str(response.json().get("id"))
                self.promoter_cache[key] = pid
                return pid
        except:
            pass
        return DEFAULT_PROMOTER_ID

    def map_tender_to_payload(self, tender):
        def to_iso(date_str):
            if not date_str: return None
            try:
                d, m, y = map(int, date_str.split('.'))
                return datetime(y, m, d).isoformat() + "Z"
            except:
                return None
        pub = to_iso(tender.date_publication) or datetime.now().isoformat() + "Z"
        exp = to_iso(tender.date_limite) or (datetime.now() + timedelta(days=30)).isoformat() + "Z"
        promoter_id = self.get_or_create_promoter(tender.autorite)
        batches = [{"title": lot, "activitiesIds": [], "deposit": "0"} for lot in tender.lots]
        return {
            "title": tender.description[:1000], "description": tender.description,
            "reference": tender.reference or f"GIZ_{tender.project_id}",
            "publicationDate": pub, "expirationDate": exp, "avisId": int(DEFAULT_AVIS_ID),
            "sourceId": int(DEFAULT_SOURCE_ID), "promoterId": int(promoter_id),
            "type": "international", "nature": "public", "isEnabled": True,
            "fundingSource": "GIZ", "currencyId": 111, "batches": batches,
            "addresses": [{"countryId": int(DEFAULT_PAYS_ID)}]
        }

    def send_tender_to_api(self, tender):
        if not self.login_appeloffres():
            return {"success": False, "message": "Connexion API échouée"}
        try:
            response = requests.post(TENDER_ENDPOINT, json=self.map_tender_to_payload(tender),
                                   headers={"Authorization": f"Bearer {self.access_token}"}, timeout=30)
            if response.status_code in [200, 201]:
                return {"success": True, "message": "Envoyé"}
            return {"success": False, "message": f"Erreur {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def scrape_and_process(self, date_debut, date_fin, categories):
        self.tenders_cache = []
        tenders = self.get_tenders_in_range(date_debut, date_fin)
        for tender in tenders:
            if tender.project_id:
                tender = self.get_project_details(tender)
                for i, url in enumerate(tender.pdf_links):
                    path = self.download_document(url, f"GIZ_{tender.project_id}_doc{i+1}.pdf")
                    if path:
                        self.extract_from_pdf(path, tender)
            self.tenders_cache.append(tender)
        return self.tenders_cache

    def get_tenders_cache(self):
        return [asdict(t) for t in self.tenders_cache]

    def update_tender(self, project_id, data):
        for t in self.tenders_cache:
            if t.project_id == project_id:
                for k, v in data.items():
                    if hasattr(t, k):
                        setattr(t, k, v)
                return True
        return False

# Flask App
app = Flask(__name__)
CORS(app)
scraper = GIZScraper()

# HTML intégré
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>GIZ Scraper</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { padding: 20px; background: #f8f9fa; }
    .card { margin-bottom: 20px; }
    .table th { background: #e9ecef; }
    .btn-sm { font-size: 0.8rem; }
    #results { display: none; }
  </style>
</head>
<body>
<div class="container">
  <h1 class="text-center mb-4">GIZ Appel d'Offres Scraper</h1>

  <div class="card">
    <div class="card-body">
      <form id="scrapeForm">
        <div class="row g-3">
          <div class="col-md-5">
            <label class="form-label">Date début</label>
            <input type="date" class="form-control" id="date_debut" required>
          </div>
          <div class="col-md-5">
            <label class="form-label">Date fin</label>
            <input type="date" class="form-control" id="date_fin" required>
          </div>
          <div class="col-md-2 d-flex align-items-end">
            <button type="submit" class="btn btn-primary w-100">Lancer</button>
          </div>
        </div>
      </form>
    </div>
  </div>

  <div id="loading" class="alert alert-info" style="display:none;">
    Scraping en cours...
  </div>

  <div id="results">
    <div class="d-flex justify-content-between mb-" style="margin-bottom: 1rem;">
      <h3>Résultats (<span id="count">0</span>)</h3>
      <button id="sendAll" class="btn btn-success">Tout envoyer</button>
    </div>

    <div class="table-responsive">
      <table class="table table-striped table-hover" id="tendersTable">
        <thead>
          <tr>
            <th>Date Pub</th>
            <th>Date Limite</th>
            <th>Description</th>
            <th>Pays</th>
            <th>Réf</th>
            <th>PDF</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
  </div>
</div>

<script>
async function scrape() {
  const debut = document.getElementById('date_debut').value;
  const fin = document.getElementById('date_fin').value;
  if (!debut || !fin) return alert("Veuillez remplir les dates");

  document.getElementById('loading').style.display = 'block';
  document.getElementById('results').style.display = 'none';

  const res = await fetch('/scrape', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({date_debut: debut, date_fin: fin})
  });
  const data = await res.json();

  document.getElementById('loading').style.display = 'none';
  if (!data.success) return alert(data.message);

  const tbody = document.querySelector('#tendersTable tbody');
  tbody.innerHTML = '';
  document.getElementById('count').textContent = data.count;
  document.getElementById('results').style.display = 'block';

  data.tenders.forEach(t => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${t.date_publication}</td>
      <td>${t.date_limite}</td>
      <td><small>${t.description.substring(0, 80)}...</small></td>
      <td>${t.pays || '—'}</td>
      <td>${t.reference || '—'}</td>
      <td>${t.pdf_links.length > 0 ? 'Oui' : 'Non'}</td>
      <td>
        <button class="btn btn-sm btn-warning me-1" onclick="edit('${t.project_id}')">Éditer</button>
        <button class="btn btn-sm btn-success me-1" onclick="send('${t.project_id}')">Envoyer</button>
        ${t.pdf_links.length > 0 ? `<a href="/download_pdf/${t.project_id}" class="btn btn-sm btn-secondary">PDF</a>` : ''}
      </td>
    `;
    tbody.appendChild(row);
  });
}

async function send(id) {
  if (!confirm("Envoyer cet appel d'offres ?")) return;
  const res = await fetch(`/send/${id}`, {method: 'POST'});
  const data = await res.json();
  alert(data.message);
  if (data.success) location.reload();
}

async function sendAll() {
  if (!confirm("Envoyer TOUS les appels d'offres ?")) return;
  const res = await fetch('/send_all', {method: 'POST'});
  const data = await res.json();
  alert(`Envoyés: ${data.success_count}/${data.total}`);
  location.reload();
}

function edit(id) {
  const desc = prompt("Nouvelle description:");
  if (desc) {
    fetch(`/update/${id}`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({description: desc})
    }).then(() => location.reload());
  }
}

document.getElementById('scrapeForm').onsubmit = (e) => { e.preventDefault(); scrape(); };
document.getElementById('sendAll').onclick = sendAll;
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

def background_scrape_giz(date_debut, date_fin):
    """Scraping en arrière-plan"""
    import threading
    try:
        tenders = scraper.scrape_and_process(date_debut, date_fin, [])
        print(f"✅ Scraping GIZ terminé: {len(tenders)} offres extraites")
    except Exception as e:
        print(f"❌ Erreur scraping GIZ en arrière-plan: {e}")

@app.route('/scrape', methods=['POST'])
def scrape():
    try:
        data = request.json
        date_debut = data.get('date_debut')
        date_fin = data.get('date_fin')
        if not date_debut or not date_fin:
            return jsonify({"success": False, "message": "Dates requises"}), 400
        tenders = scraper.scrape_and_process(date_debut, date_fin, [])
        return jsonify({
            "success": True,
            "tenders": scraper.get_tenders_cache(),
            "count": len(tenders)
        })
    except Exception as e:
        logger.error(f"Erreur scrape: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """Lance le scraping via API avec plage de dates (en arrière-plan)"""
    import threading
    try:
        data = request.get_json() or {}
        start_date = data.get('start', datetime.now().strftime("%Y-%m-%d"))
        end_date = data.get('end', datetime.now().strftime("%Y-%m-%d"))

        # Valider le format de date YYYY-MM-DD
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except:
            return jsonify({"success": False, "message": "Format de date invalide"}), 400

        # Lancer le scraping en arrière-plan (utiliser YYYY-MM-DD directement)
        thread = threading.Thread(target=background_scrape_giz, args=(start_date, end_date))
        thread.daemon = True
        thread.start()

        return jsonify({
            "success": True,
            "message": f"Scraping GIZ lancé pour la période du {start_date} au {end_date}",
            "count": 0
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/update/<project_id>', methods=['POST'])
def update_tender(project_id):
    try:
        data = request.json
        if scraper.update_tender(project_id, data):
            return jsonify({"success": True, "message": "Mis à jour"})
        return jsonify({"success": False, "message": "Non trouvé"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/send/<project_id>', methods=['POST'])
def send_tender(project_id):
    try:
        for tender in scraper.tenders_cache:
            if tender.project_id == project_id:
                result = scraper.send_tender_to_api(tender)
                if result['success']:
                    scraper.tenders_cache = [t for t in scraper.tenders_cache if t.project_id != project_id]
                return jsonify(result)
        return jsonify({"success": False, "message": "Non trouvé"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/send_all', methods=['POST'])
def send_all_tenders():
    try:
        results = []
        for tender in scraper.tenders_cache[:]:
            result = scraper.send_tender_to_api(tender)
            results.append({"project_id": tender.project_id, **result})
        scraper.tenders_cache = []
        success_count = sum(1 for r in results if r['success'])
        return jsonify({
            "success": True,
            "total": len(results),
            "success_count": success_count,
            "results": results
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/download_pdf/<project_id>')
def download_pdf(project_id):
    try:
        for tender in scraper.tenders_cache:
            if tender.project_id == project_id and tender.pdf_links:
                filename = f"GIZ_{project_id}_doc1.pdf"
                filepath = os.path.join(PDF_DIR, filename)
                if os.path.exists(filepath):
                    return send_file(filepath, as_attachment=True, download_name=filename)
        return "PDF non trouvé", 404
    except Exception as e:
        logger.error(f"Erreur download: {e}")
        return "Erreur", 500

# API Endpoints pour le frontend React
@app.route('/pending-all', methods=['GET'])
@app.route('/api/pending-all', methods=['GET'])
def api_pending_all():
    """Retourne toutes les offres pending pour le frontend React"""
    try:
        # Convertir les tenders_cache en format compatible avec le frontend
        offers = []
        for tender in scraper.tenders_cache:
            tender_dict = asdict(tender)
            # Mapper les champs GIZ vers le format attendu par le frontend
            transformed_offer = {
                '_id': tender_dict.get('project_id', ''),
                'reference': tender_dict.get('reference', ''),
                'description': tender_dict.get('description', ''),
                'promoter': 'GIZ',
                'date_publication': tender_dict.get('date_publication', ''),
                'date_limite': tender_dict.get('date_limite', ''),
                'country': tender_dict.get('pays', ''),
                'pdf_links': tender_dict.get('pdf_links', []),
                # Garder aussi les champs originaux
                'project_id': tender_dict.get('project_id', ''),
                'title': tender_dict.get('description', ''),
                'publication_date': tender_dict.get('date_publication', ''),
                'deadline_date': tender_dict.get('date_limite', ''),
                'tender_type': tender_dict.get('type', ''),
                'tender_volume': '',
                'project_url': tender_dict.get('lien_details', ''),
                'autorite': tender_dict.get('autorite', ''),
                'secteur_activite': tender_dict.get('secteur_activite', '')
            }
            offers.append(transformed_offer)

        return jsonify({
            "success": True,
            "offres": offers,
            "count": len(offers)
        })
    except Exception as e:
        logger.error(f"Erreur API pending-all: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/validated-all', methods=['GET'])
@app.route('/api/validated-all', methods=['GET'])
def api_validated_all():
    """Retourne toutes les offres validées (GIZ n'a pas de système de validation MongoDB)"""
    return jsonify({
        "success": True,
        "offres": [],
        "count": 0
    })

@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        return jsonify({
            "status": "ok",
            "pending": len(scraper.tenders_cache),
            "validated": 0
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    logger.info("Démarrage serveur Flask GIZ")
    app.run(debug=True, port=5014, host='0.0.0.0', use_reloader=False)