// routes/tuneps.js - VERSION FINALE COMPLÈTE AVEC /validated + API AppelOffres
const express = require('express');
const router = express.Router();
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const mongoose = require('mongoose');
const axios = require('axios');
const { Pool } = require('pg');
require('dotenv').config();

// ===== CONNEXION POSTGRESQL =====
const pgPool = new Pool({
  host: process.env.DB_HOST || 'localhost',  // ✅ localhost par défaut
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || 'tenders_db',
  user: process.env.DB_USER || 'tender_user',
  password: process.env.DB_PASSWORD || 'tender_password_2024',
});

console.log('📊 PostgreSQL Pool created for TUNEPS routes');

// ===== SCHÉMA MONGODB =====
const OffreSchema = new mongoose.Schema({
  reference: { type: String, required: true, unique: true },
  description: String,
  full_content: String,
  promoter: String,
  publicationDate: String,
  startBiddingDate: String,
  expirationDate: String,
  ouverture_offres: String,
  offer_validity_duration: String,
  cautionnement_provisoire: String,
  cahier_charge_pdf: String,
  cahier_charge_pdf_filename: String,
  cahier_charge_url: String,
  image_filename: String,
  image_path: String,
  s3_image_url: String,
  lots: Array,
  pieces_jointes: Array,
  procedure: String,
  type_marche: String,
  type: String,
  url_source: String,
  status: { type: String, enum: ['pending', 'validated', 'active'], default: 'pending' },
  region_id: Number,
  mots_cles_detectes: Array,
  sourceId: String,
  promoterId: String,
  nature: String,
  fundingSource: String,
  fundingSourceType: String,
  isMultiCurrency: Boolean,
  currencyId: String,
  pays: String,
  avis: String,
  createdAt: { type: Date, default: Date.now },
  updatedAt: { type: Date, default: Date.now },
  extractionDate: String,
  validationDate: String
}, { 
  collection: 'pending_tenders_marmoucha',
  strict: false 
});

const Offre = mongoose.models.Offre || mongoose.model('Offre', OffreSchema);

// ===== CONFIGURATION API APPELOFFRES =====
// IMPORTANT: Utiliser les mêmes credentials que tuneps.py (ceux qui fonctionnent!)
const API_BASE_URL = 'https://be.appeloffres.net/api'; // Production, pas staging
const API_EMAIL = 'maryam.marmouch@tunipages.tn';
const API_PASSWORD = 'Marmouch2345!@';
const LOGIN_ENDPOINT = `${API_BASE_URL}/auth/login/`;
const TENDER_ENDPOINT = `${API_BASE_URL}/tender`;
const DEFAULT_SOURCE_ID = '817';
const DEFAULT_PROMOTER_ID = '223472';
const DEFAULT_AVIS_ID = '2'; // Utiliser 2 comme dans tuneps.py
const DEFAULT_PAYS_ID = '219';
const DEFAULT_CURRENCY_ID = '111';

let accessToken = null;

// Fonction pour se connecter à l'API AppelOffres
async function loginAppelOffres() {
  if (accessToken) {
    return accessToken;
  }

  try {
    console.log(`🔐 Connexion à l'API AppelOffres: ${LOGIN_ENDPOINT}`);
    const response = await axios.post(LOGIN_ENDPOINT, {
      email: API_EMAIL,
      password: API_PASSWORD
    }, {
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      timeout: 1800000
    });

    if (response.status === 200 || response.status === 201) {
      accessToken = response.data.accessToken;
      console.log('✅ Connexion API AppelOffres réussie');
      return accessToken;
    } else {
      console.error(`❌ Erreur connexion API: Status ${response.status}`);
      return null;
    }
  } catch (error) {
    console.error('❌ Erreur lors de la connexion API:', error.message);
    return null;
  }
}

// Fonction pour parser et formater les dates en ISO
function parseDate(dateStr) {
  if (!dateStr || dateStr === 'N/A') return null;

  // Convertir en string si ce n'est pas déjà le cas
  const dateString = typeof dateStr === 'string' ? dateStr : String(dateStr);

  if (dateString.trim() === '') return null;

  try {
    // Format français: DD/MM/YYYY HH:MM
    const frenchDatePattern = /^(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{2})$/;
    const match = dateString.match(frenchDatePattern);

    if (match) {
      const [, day, month, year, hour, minute] = match;
      // Créer une date ISO (les mois en JS commencent à 0)
      const date = new Date(
        parseInt(year),
        parseInt(month) - 1,
        parseInt(day),
        parseInt(hour),
        parseInt(minute),
        0
      );

      if (!isNaN(date.getTime())) {
        return date.toISOString();
      }
    }

    // Sinon, essayer le parsing standard
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return null;
    return date.toISOString();
  } catch (e) {
    return null;
  }
}

// Fonction pour nettoyer les montants de dépôt
function cleanDeposit(depositStr) {
  if (!depositStr) return "0";
  const cleaned = String(depositStr).replace(/[^\d\s,.]/g, '').trim();
  return cleaned || "0";
}

// Fonction pour mapper l'offre au format API (EXACTEMENT comme tuneps.py)
function mapOffreToTenderPayload(offre) {
  // Parser les dates
  let publicationDate = parseDate(offre.publicationDate);
  let startBiddingDate = parseDate(offre.startBiddingDate);
  let expirationDate = parseDate(offre.expirationDate);
  const openingBidsDate = parseDate(offre.ouverture_offres);

  // Si pas de publicationDate, utiliser maintenant
  if (!publicationDate) {
    const now = new Date();
    publicationDate = now.toISOString();
  }

  // Si pas de startBiddingDate, utiliser publicationDate
  if (!startBiddingDate) {
    startBiddingDate = publicationDate;
  }

  // Si pas de date d'expiration, calculer +30 jours depuis publicationDate
  if (!expirationDate) {
    const pubDate = new Date(publicationDate);
    pubDate.setDate(pubDate.getDate() + 30);
    pubDate.setHours(12, 0, 0, 0);
    expirationDate = pubDate.toISOString();
  }

  // Construire les batches (lots)
  let batches = [];
  if (offre.lots && offre.lots.length > 0) {
    batches = offre.lots.map((lot, i) => {
      const title = lot.title || lot.objet || lot.description || `Lot ${i + 1}`;
      const deposit = cleanDeposit(lot['Cautionnement provisoire'] || lot.deposit || offre.cautionnement_provisoire);
      return {
        activitiesIds: [],
        title: title,
        deposit: deposit
      };
    });
  }

  // Si pas de lots, créer un batch unique avec la description
  if (batches.length === 0) {
    const description = offre.description || `Appel d'offres TUNEPS - Reference: ${offre.reference}`;
    const deposit = cleanDeposit(offre.cautionnement_provisoire);
    batches = [{
      activitiesIds: [],
      title: description,
      deposit: deposit
    }];
  }

  // Construire le titre
  const rawDescription = offre.description || `Appel d'offres TUNEPS - Reference: ${offre.reference}`;
  let title = rawDescription;

  // Construire les addresses
  const addresses = [{
    countryId: DEFAULT_PAYS_ID
  }];
  if (offre.region_id) {
    addresses[0].regionId = String(offre.region_id);
  }

  // Construire les images
  let images = [];
  if (offre.s3_image_url) {
    const match = offre.s3_image_url.match(/\/tender-s3-prod\/(.+?\.(?:png|pdf))/);
    if (match) {
      images = [{
        url: match[1],
        description: "Image officielle TUNEPS - Système Tunisien de l'E-Procurement"
      }];
    }
  }

  // ✅ TOUJOURS utiliser l'image fixe TUNEPS (pas besoin d'URL S3)
  // L'image sera uploadée automatiquement par l'API AppelOffres
  images = [{
    url: "tuneps_default.png",
    description: "Image officielle TUNEPS - Système Tunisien de l'E-Procurement"
  }];

  // Déterminer le type (national/international)
  const fullText = (offre.description || '') + ' ' + (offre.full_content || '');
  const type = fullText.toLowerCase().includes('international') ? 'international' : 'national';

  // Construire le payload EXACTEMENT comme tuneps.py
  const payload = {
    title: title,
    description: rawDescription,
    publicationDate: publicationDate,
    startBiddingDate: startBiddingDate,
    expirationDate: expirationDate,
    openingBidsDate: openingBidsDate,
    reference: offre.reference,
    specificationsPrice: 0,
    offerValidityPeriode: offre.offer_validity_duration && offre.offer_validity_duration !== 'N/A' ? offre.offer_validity_duration : null,
    avisId: parseInt(DEFAULT_AVIS_ID),
    sourceId: parseInt(DEFAULT_SOURCE_ID),
    promoterId: parseInt(offre.promoterId || DEFAULT_PROMOTER_ID),
    type: type,
    nature: offre.nature || null,
    isEnabled: true,
    specificationsReceivingAddress: offre.url_source || "URL non disponible",
    fundingSourceType: "national",
    fundingSource: offre.fundingSource || null,
    currencyId: parseInt(DEFAULT_CURRENCY_ID),
    isMultiCurrency: offre.isMultiCurrency || false,
    batches: batches,
    addresses: addresses,
    images: images
  };

  // Filtrer les valeurs null et vides
  const filteredPayload = {};
  for (const [key, value] of Object.entries(payload)) {
    if (value !== null && value !== '') {
      filteredPayload[key] = value;
    }
  }

  return filteredPayload;
}

// Fonction pour créer ou récupérer un promoteur
async function getOrCreatePromoter(promoterName) {
  if (!promoterName || promoterName.trim() === '') {
    promoterName = 'Promoteur TUNEPS Inconnu';
  }

  try {
    const token = await loginAppelOffres();
    if (!token) {
      console.error('❌ Impossible de se connecter pour créer le promoteur');
      return DEFAULT_PROMOTER_ID;
    }

    // Créer le promoteur
    const promoterPayload = {
      name: promoterName,
      description: `Acheteur public TUNEPS: ${promoterName}`,
      reference: promoterName.replace(/\W+/g, '_').toUpperCase().substring(0, 20),
      isEnabled: true,
      companyName: promoterName,
      address: {
        street: "Adresse inconnue",
        city: "Tunis",
        country: "Tunisie",
        postalCode: "1000"
      }
    };

    console.log(`📝 Création du promoteur: ${promoterName}`);
    const response = await axios.post('https://be.appeloffres.net/api/promoter', promoterPayload, {
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      timeout: 30000
    });

    if (response.status === 200 || response.status === 201) {
      const promoterId = response.data.id || response.data.promoterId;
      console.log(`✅ Promoteur créé avec ID: ${promoterId}`);
      return promoterId;
    } else {
      console.warn(`⚠️ Erreur création promoteur, utilisation de l'ID par défaut`);
      return DEFAULT_PROMOTER_ID;
    }
  } catch (error) {
    // Si le promoteur existe déjà (erreur 409), c'est normal
    if (error.response && error.response.status === 409) {
      console.log(`ℹ️ Promoteur "${promoterName}" existe déjà, utilisation de l'ID par défaut`);
      return DEFAULT_PROMOTER_ID;
    }
    console.error(`❌ Erreur création promoteur: ${error.message}`);
    return DEFAULT_PROMOTER_ID;
  }
}

// Fonction pour envoyer l'offre vers l'API AppelOffres
async function postTenderToAPI(offre) {
  try {
    const token = await loginAppelOffres();
    if (!token) {
      console.error('❌ Impossible de se connecter à l\'API AppelOffres');
      return {
        success: false,
        message: 'Échec de connexion à l\'API AppelOffres'
      };
    }

    // Créer ou récupérer le promoteur si nécessaire
    let promoterId = offre.promoterId;
    if (!promoterId || promoterId === DEFAULT_PROMOTER_ID) {
      promoterId = await getOrCreatePromoter(offre.promoter);
    }

    // Mettre à jour l'offre avec le bon promoterId
    offre.promoterId = promoterId;

    const payload = mapOffreToTenderPayload(offre);
    console.log(`📤 Envoi de l'offre ${offre.reference} vers l'API AppelOffres...`);
    console.log('📋 Payload complet:', JSON.stringify(payload, null, 2));

    const response = await axios.post(TENDER_ENDPOINT, payload, {
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      timeout: 30000
    });

    if (response.status === 200 || response.status === 201) {
      console.log(`✅ Offre ${offre.reference} envoyée avec succès à l'API AppelOffres`);
      return {
        success: true,
        message: 'Offre envoyée vers AppelOffres',
        apiResponse: response.data
      };
    } else {
      console.error(`❌ Erreur API: Status ${response.status}`, response.data);
      return {
        success: false,
        message: `Erreur API: ${response.status}`,
        apiResponse: response.data
      };
    }
  } catch (error) {
    console.error('❌ Erreur lors de l\'envoi vers l\'API:', error.message);
    return {
      success: false,
      message: `Erreur lors de l'envoi: ${error.message}`
    };
  }
}

// État du scraping
let scrapingState = {
  isProcessing: false,
  process: null,
  startTime: null,
  result: null,
  error: null
};

// Chemin vers le script Python
const PYTHON_SCRIPT = path.join(__dirname, '..', 'scripts', 'tuneps.py');

// ===== ROUTES =====

// Route de test
router.get('/test', (req, res) => {
  console.log('✅ Route /api/tuneps/test appelée');
  res.json({
    success: true,
    message: 'TUNEPS API is working',
    timestamp: new Date().toISOString(),
    pythonScript: fs.existsSync(PYTHON_SCRIPT) ? 'found' : 'not found',
    database: 'marmoucha',
    collections: {
      pending: 'pending_tenders_marmoucha',
      validated: 'tenders_marmoucha'
    }
  });
});

// Route pour vérifier l'état du scraping
router.get('/status', (req, res) => {
  console.log('✅ Route /api/tuneps/status appelée');
  res.json({
    success: true,
    scraping: scrapingState.isProcessing ? {
      isProcessing: true,
      startTime: scrapingState.startTime,
      duration: Math.floor((Date.now() - scrapingState.startTime) / 1000)
    } : {
      isProcessing: false,
      message: 'Ready'
    }
  });
});

// Route pour lancer le scraping Python
router.post('/scrape', async (req, res) => {
  console.log('✅ Route /api/tuneps/scrape appelée avec body:', req.body);
  
  if (scrapingState.isProcessing) {
    return res.status(400).json({
      success: false,
      message: 'Scraping déjà en cours. Veuillez attendre.',
      startTime: scrapingState.startTime
    });
  }

  const { start_date, end_date, extraction_complete = false } = req.body;
  
  console.log('🚀 Démarrage du scraping Python TUNEPS...');
  console.log('📅 Dates:', start_date, 'à', end_date);
  console.log('🔍 Mode:', extraction_complete ? 'complet' : 'rapide');

  scrapingState = {
    isProcessing: true,
    process: null,
    startTime: Date.now(),
    result: null,
    error: null
  };

  const args = [PYTHON_SCRIPT, '--scrape'];
  
  if (start_date) args.push('--start-date', start_date);
  if (end_date) args.push('--end-date', end_date);
  if (extraction_complete) args.push('--complete');

  try {
    const pythonProcess = spawn('python', args, {
      cwd: path.dirname(PYTHON_SCRIPT),
      stdio: ['pipe', 'pipe', 'pipe']
    });

    scrapingState.process = pythonProcess;

    let output = '';
    let errorOutput = '';

    pythonProcess.stdout.on('data', (data) => {
      const text = data.toString();
      output += text;
      console.log('📝 Python stdout:', text.trim());
    });

    pythonProcess.stderr.on('data', (data) => {
      const text = data.toString();
      errorOutput += text;
      console.error('❌ Python stderr:', text.trim());
    });

    pythonProcess.on('close', (code) => {
      console.log(`✅ Script Python terminé avec code: ${code}`);
      
      if (code === 0) {
        scrapingState.result = {
          success: true,
          output: output,
          duration: Math.floor((Date.now() - scrapingState.startTime) / 1000)
        };
      } else {
        scrapingState.error = {
          success: false,
          error: errorOutput || `Script Python échoué avec code ${code}`,
          output: output
        };
      }
      
      scrapingState.isProcessing = false;
    });

    pythonProcess.on('error', (err) => {
      console.error('❌ Erreur exécution Python:', err);
      scrapingState.error = {
        success: false,
        error: err.message
      };
      scrapingState.isProcessing = false;
    });

    res.json({
      success: true,
      message: 'Scraping Python démarré avec succès',
      pid: pythonProcess.pid,
      params: { start_date, end_date, extraction_complete },
      note: 'Suivez la progression avec GET /api/tuneps/status'
    });

  } catch (error) {
    console.error('❌ Erreur lancement scraping:', error);
    scrapingState.error = { success: false, error: error.message };
    scrapingState.isProcessing = false;
    
    res.status(500).json({
      success: false,
      message: 'Erreur lors du lancement du scraping',
      error: error.message
    });
  }
});

// Route pour obtenir les offres en attente (pending) - POSTGRESQL VERSION
router.get('/pending', async (req, res) => {
  console.log('✅ Route /api/tuneps/pending appelée (PostgreSQL)');

  try {
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 100;
    const offset = (page - 1) * limit;

    // Interroger PostgreSQL pour les offres avec status='pending'
    const countQuery = `
      SELECT COUNT(*) as total
      FROM tenders_tuneps
      WHERE status = 'pending'
    `;

    const offersQuery = `
      SELECT *
      FROM tenders_tuneps
      WHERE status = 'pending'
      ORDER BY extraction_date DESC
      LIMIT $1 OFFSET $2
    `;

    const countResult = await pgPool.query(countQuery);
    const total = parseInt(countResult.rows[0]?.total || 0);

    const offersResult = await pgPool.query(offersQuery, [limit, offset]);
    const offers = offersResult.rows.map(row => ({
      ...row,
      _id: row.id?.toString() || '',
      extractionDate: row.extraction_date || '',
      publicationDate: row.publication_date || '',
      expirationDate: row.expiration_date || '',
      openingDate: row.opening_date || '',
      startBiddingDate: row.start_bidding_date || '',
      promoter: row.promoter || '',
      s3_image_url: row.s3_image_url || ''
    }));

    console.log(`📊 Réponse pending (PostgreSQL): ${offers.length} offres sur ${total} total`);

    res.json({
      success: true,
      data: {
        offers: offers,
        pagination: {
          page,
          limit,
          total,
          totalPages: Math.ceil(total / limit)
        }
      },
      scraping: {
        isProcessing: scrapingState.isProcessing,
        startTime: scrapingState.startTime
      }
    });
  } catch (error) {
    console.error('❌ Erreur récupération offres pending (PostgreSQL):', error);

    res.json({
      success: true,
      data: {
        offers: [],
        pagination: {
          page: 1,
          limit: 100,
          total: 0,
          totalPages: 0
        }
      },
      scraping: {
        isProcessing: false,
        message: "PostgreSQL error - check connection"
      },
      error: error.message
    });
  }
});

// ✅ ROUTE POUR OBTENIR LES OFFRES VALIDÉES - POSTGRESQL VERSION
router.get('/validated', async (req, res) => {
  console.log('✅ Route /api/tuneps/validated appelée (PostgreSQL)');

  try {
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 100;
    const offset = (page - 1) * limit;

    // Interroger PostgreSQL pour les offres avec status='active' (validées et envoyées à l'API)
    const countQuery = `
      SELECT COUNT(*) as total
      FROM tenders_tuneps
      WHERE status = 'active'
    `;

    const tendersQuery = `
      SELECT *
      FROM tenders_tuneps
      WHERE status = 'active'
      ORDER BY extraction_date DESC
      LIMIT $1 OFFSET $2
    `;

    const countResult = await pgPool.query(countQuery);
    const total = parseInt(countResult.rows[0]?.total || 0);

    const tendersResult = await pgPool.query(tendersQuery, [limit, offset]);
    const tenders = tendersResult.rows.map(row => ({
      ...row,
      _id: row.id?.toString() || '',
      extractionDate: row.extraction_date || '',
      validationDate: row.validation_date || '',
      publicationDate: row.publication_date || '',
      expirationDate: row.expiration_date || '',
      openingDate: row.opening_date || '',
      startBiddingDate: row.start_bidding_date || ''
    }));

    console.log(`📊 Réponse validated (PostgreSQL): ${tenders.length} offres sur ${total} total (table: tenders_tuneps, status=active)`);

    res.json({
      success: true,
      tenders: tenders,
      count: tenders.length,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit)
      }
    });
  } catch (error) {
    console.error('❌ Erreur récupération validées:', error);
    res.json({
      success: true,
      tenders: [],
      count: 0,
      error: error.message
    });
  }
});

// Route pour valider une offre (PostgreSQL + envoyer vers API) - COMME BOAMP
router.post('/validate/:reference', async (req, res) => {
  console.log('✅ Route /api/tuneps/validate appelée pour:', req.params.reference);

  try {
    const reference = req.params.reference;

    // 1. Récupérer l'offre depuis PostgreSQL (n'importe quel status - PERMETTRE RE-VALIDATION)
    const pendingQuery = 'SELECT * FROM tenders_tuneps WHERE reference = $1 LIMIT 1';
    const pendingResult = await pgPool.query(pendingQuery, [reference]);

    if (pendingResult.rows.length === 0) {
      return res.status(404).json({
        success: false,
        message: `Offre ${reference} non trouvée dans la base`
      });
    }

    const pendingOffer = pendingResult.rows[0];

    // ✅ Log du status actuel
    console.log(`📊 Offre ${reference} trouvée - Status actuel: ${pendingOffer.status || 'pending'}`);
    if (pendingOffer.status === 'active') {
      console.log(`⚠️ ATTENTION: Cette offre est déjà validée (active) - RE-VALIDATION en cours...`);
    }

    // Convertir les noms de colonnes PostgreSQL en format attendu
    const offreFormatted = {
      reference: pendingOffer.reference,
      description: pendingOffer.description,
      full_content: pendingOffer.full_content,
      promoter: pendingOffer.promoter,
      publicationDate: pendingOffer.publication_date,
      expirationDate: pendingOffer.expiration_date,
      openingDate: pendingOffer.opening_date,
      startBiddingDate: pendingOffer.start_bidding_date,
      region_id: pendingOffer.region_id,
      promoterId: pendingOffer.promoter_id,
      sourceId: pendingOffer.source_id || DEFAULT_SOURCE_ID,
      avisId: pendingOffer.avis_id || DEFAULT_AVIS_ID,
      paysId: pendingOffer.pays_id || DEFAULT_PAYS_ID,
      currencyId: pendingOffer.currency_id || DEFAULT_CURRENCY_ID,
      nature: pendingOffer.nature || 'public',
      s3_image_url: pendingOffer.s3_image_url || '',
      url_source: pendingOffer.external_url || '',
      lots: Array.isArray(pendingOffer.batches) ? pendingOffer.batches :
            (typeof pendingOffer.batches === 'string' && pendingOffer.batches && pendingOffer.batches !== '' && pendingOffer.batches !== 'null') ?
            JSON.parse(pendingOffer.batches) : [],
      offer_validity_duration: pendingOffer.offer_validity_period,
      cautionnement_provisoire: pendingOffer.cautionnement || '0'
    };

    // 2. ENVOYER VERS L'API APPELOFFRES AVEC IMAGE
    console.log(`📤 Tentative d'envoi de l'offre ${reference} vers l'API AppelOffres...`);
    console.log(`📸 Image utilisée: tuneps_default.png (image fixe TUNEPS)`);

    const apiResult = await postTenderToAPI(offreFormatted);

    // ❌ SI L'API ÉCHOUE, NE PAS VALIDER L'OFFRE
    if (!apiResult.success) {
      console.error(`❌ ÉCHEC ENVOI API pour ${reference}: ${apiResult.message}`);
      console.error(`⚠️ L'offre reste en PENDING - elle ne sera PAS validée`);
      return res.status(500).json({
        success: false,
        message: `❌ Échec de l'envoi vers l'API AppelOffres: ${apiResult.message}`,
        details: apiResult,
        reference: reference,
        note: "L'offre reste en pending - corrigez l'erreur et réessayez"
      });
    }

    console.log(`✅ Offre ${reference} envoyée avec SUCCÈS à l'API AppelOffres`);
    console.log(`✅ API Response ID: ${apiResult.apiResponse?.id}`);

    // 3. SEULEMENT MAINTENANT, marquer comme validée dans PostgreSQL
    const updateQuery = `
      UPDATE tenders_tuneps
      SET status = 'active', validation_date = $1, api_id = $2
      WHERE reference = $3
    `;
    const validationDate = new Date().toISOString();
    const apiId = apiResult.apiResponse?.id || null;

    await pgPool.query(updateQuery, [validationDate, apiId, reference]);

    console.log(`✅ Offre ${reference} validée et marquée active dans PostgreSQL (API ID: ${apiId})`);

    res.json({
      success: true,
      message: `Offre ${reference} validée et envoyée à l'API avec succès`,
      reference: reference,
      validationDate: validationDate,
      apiSent: true,
      apiMessage: apiResult.message,
      apiResponse: apiResult.apiResponse || null
    });
  } catch (error) {
    console.error('❌ Erreur validation:', error);
    res.status(500).json({
      success: false,
      message: 'Erreur lors de la validation',
      error: error.message
    });
  }
});

// Route pour supprimer une offre pending - POSTGRESQL VERSION
router.delete('/delete/:reference', async (req, res) => {
  console.log('✅ Route /api/tuneps/delete appelée pour:', req.params.reference);

  try {
    const reference = req.params.reference;

    const deleteQuery = `
      DELETE FROM tenders_tuneps
      WHERE reference = $1 AND status = 'pending'
      RETURNING *
    `;

    const result = await pgPool.query(deleteQuery, [reference]);

    if (result.rowCount === 0) {
      return res.status(404).json({
        success: false,
        message: `Offre ${reference} non trouvée dans pending`
      });
    }

    console.log(`✅ Offre pending ${reference} supprimée de PostgreSQL`);

    res.json({
      success: true,
      message: `Offre ${reference} supprimée`,
      reference: reference
    });
  } catch (error) {
    console.error('❌ Erreur suppression (PostgreSQL):', error);
    res.status(500).json({
      success: false,
      message: 'Erreur lors de la suppression',
      error: error.message
    });
  }
});

// Route pour supprimer TOUTES les offres pending - POSTGRESQL VERSION
router.delete('/delete-all', async (req, res) => {
  console.log('✅ Route /api/tuneps/delete-all appelée');

  try {
    const deleteQuery = `
      DELETE FROM tenders_tuneps
      WHERE status = 'pending'
    `;

    const result = await pgPool.query(deleteQuery);
    const deletedCount = result.rowCount;

    console.log(`✅ ${deletedCount} offres pending supprimées de PostgreSQL`);

    res.json({
      success: true,
      message: `${deletedCount} offres supprimées`,
      deletedCount: deletedCount
    });
  } catch (error) {
    console.error('❌ Erreur suppression globale (PostgreSQL):', error);
    res.status(500).json({
      success: false,
      message: 'Erreur lors de la suppression',
      error: error.message
    });
  }
});

// ✅ ROUTE POUR SUPPRIMER UNE OFFRE VALIDÉE - POSTGRESQL VERSION
router.delete('/validated/delete/:reference', async (req, res) => {
  console.log('✅ Route /api/tuneps/validated/delete appelée pour:', req.params.reference);

  try {
    const reference = req.params.reference;

    // Supprimer de PostgreSQL
    const deleteQuery = `
      DELETE FROM tenders_tuneps
      WHERE reference = $1 AND status = 'active'
      RETURNING *
    `;

    const result = await pgPool.query(deleteQuery, [reference]);

    if (result.rowCount === 0) {
      return res.status(404).json({
        success: false,
        message: `Offre validée ${reference} non trouvée dans PostgreSQL`
      });
    }

    console.log(`✅ Offre validée ${reference} supprimée de tenders_tuneps (PostgreSQL)`);

    res.json({
      success: true,
      message: `Offre validée ${reference} supprimée`,
      reference: reference
    });
  } catch (error) {
    console.error('❌ Erreur suppression validated (PostgreSQL):', error);
    res.status(500).json({
      success: false,
      message: 'Erreur lors de la suppression',
      error: error.message
    });
  }
});

// Route pour mettre à jour une offre pending
router.post('/update/:reference', async (req, res) => {
  console.log('✅ Route /api/tuneps/update appelée pour:', req.params.reference);
  
  try {
    const reference = req.params.reference;
    const updates = req.body;
    
    const result = await Offre.findOneAndUpdate(
      { reference: reference, status: 'pending' },
      { $set: { ...updates, updatedAt: new Date() } },
      { new: true }
    );

    if (!result) {
      return res.status(404).json({
        success: false,
        message: `Offre ${reference} non trouvée`
      });
    }

    console.log(`✅ Offre ${reference} mise à jour`);

    res.json({
      success: true,
      message: `Offre ${reference} mise à jour`,
      offre: result
    });
  } catch (error) {
    console.error('❌ Erreur mise à jour:', error);
    res.status(500).json({
      success: false,
      message: 'Erreur lors de la mise à jour',
      error: error.message
    });
  }
});

module.exports = router;