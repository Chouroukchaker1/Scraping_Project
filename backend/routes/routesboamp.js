// routesboamp.js - Routes pour le scraper BOAMP (Python Flask)
const express = require('express');
const router = express.Router();
const axios = require('axios');
const path = require('path');

// Configuration
const PYTHON_SERVER_URL = 'http://localhost:5003';
const PYTHON_API_TIMEOUT = 1800000; // 30 minutes timeout pour les scrapings longs (BOAMP peut traiter beaucoup d'offres)

// Middleware pour gérer les erreurs axios
const handlePythonApiError = (error, res) => {
    console.error('❌ Erreur communication avec serveur Python:', error.message);
    
    if (error.code === 'ECONNREFUSED') {
        return res.status(503).json({
            success: false,
            error: 'Serveur Python non disponible',
            message: 'Le serveur Python (port 5003) n\'est pas démarré ou inaccessible'
        });
    }
    
    if (error.response) {
        // Erreur de l'API Python
        return res.status(error.response.status).json({
            success: false,
            error: `Erreur serveur Python (${error.response.status})`,
            message: error.response.data?.error || error.response.statusText,
            details: error.response.data
        });
    }
    
    if (error.request) {
        // Pas de réponse du serveur Python
        return res.status(504).json({
            success: false,
            error: 'Timeout serveur Python',
            message: 'Le serveur Python n\'a pas répondu dans le délai imparti'
        });
    }
    
    // Autres erreurs
    return res.status(500).json({
        success: false,
        error: 'Erreur interne',
        message: error.message
    });
};

// ============================================
// ROUTES PRINCIPALES
// ============================================

// 1. Test de connexion au serveur Python
router.get('/test-python', async (req, res) => {
    try {
        const response = await axios.get(`${PYTHON_SERVER_URL}/api/test`, {
            timeout: 10000
        });
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// 2. Lancer un scraping BOAMP
router.post('/scrape', async (req, res) => {
    try {
        const { date_debut, date_fin } = req.body;
        
        console.log(`🚀 Démarrage scraping BOAMP: ${date_debut || 'auto'} à ${date_fin || 'auto'}`);
        
        const response = await axios.post(`${PYTHON_SERVER_URL}/api/scrape`, {
            date_debut,
            date_fin
        }, {
            timeout: PYTHON_API_TIMEOUT // Long timeout pour scraping
        });
        
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// 3. Obtenir les offres en attente (pending)
router.get('/pending', async (req, res) => {
    try {
        const { page = 1, limit = 100 } = req.query;
        
        const response = await axios.get(`${PYTHON_SERVER_URL}/api/pending`, {
            params: { page, limit },
            timeout: 30000
        });
        
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// 4. Valider une offre (transfert vers base validée)
router.post('/validate/:reference', async (req, res) => {
    try {
        const { reference } = req.params;
        
        console.log(`✅ Validation offre BOAMP: ${reference}`);
        
        const response = await axios.post(
            `${PYTHON_SERVER_URL}/api/validate/${reference}`,
            {},
            { timeout: 30000 }
        );
        
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// 5. Supprimer une offre en attente
router.delete('/delete/:reference', async (req, res) => {
    try {
        const { reference } = req.params;
        
        const response = await axios.delete(
            `${PYTHON_SERVER_URL}/api/delete/${reference}`,
            { timeout: 30000 }
        );
        
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// 6. Nettoyer toutes les offres en attente
router.post('/clean-pending', async (req, res) => {
    try {
        console.log('🧹 Nettoyage offres pending BOAMP');
        
        const response = await axios.post(
            `${PYTHON_SERVER_URL}/api/clean_pending`,
            {},
            { timeout: 30000 }
        );
        
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// 7. Obtenir les secteurs d'activité
router.get('/secteurs', async (req, res) => {
    try {
        const response = await axios.get(`${PYTHON_SERVER_URL}/api/secteurs`, {
            timeout: 30000
        });
        
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// 8. Obtenir le mapping BOAMP -> API
router.get('/boamp-mapping', async (req, res) => {
    try {
        const response = await axios.get(`${PYTHON_SERVER_URL}/api/boamp_mapping`, {
            timeout: 30000
        });
        
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// 9. Obtenir la liste des mots-clés BOAMP
router.get('/keywords', async (req, res) => {
    try {
        const response = await axios.get(`${PYTHON_SERVER_URL}/api/keywords`, {
            timeout: 30000
        });
        
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// 10. Vérifier l'état de santé
router.get('/health', async (req, res) => {
    try {
        const response = await axios.get(`${PYTHON_SERVER_URL}/api/health`, {
            timeout: 10000
        });
        
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// 11. Obtenir les statistiques
router.get('/stats', async (req, res) => {
    try {
        const response = await axios.get(`${PYTHON_SERVER_URL}/api/stats`, {
            timeout: 30000
        });
        
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// ============================================
// ROUTES D'ADMINISTRATION
// ============================================

// 12. Démarrer le serveur Python (si gestion via PM2)
router.post('/start-python-server', async (req, res) => {
    try {
        // Cette route peut être utilisée pour démarrer le serveur Python via PM2
        const { exec } = require('child_process');
        const pythonScriptPath = path.join(__dirname, '../backend/scripts/scraper.py');
        
        exec(`python "${pythonScriptPath}"`, (error, stdout, stderr) => {
            if (error) {
                console.error(`❌ Erreur démarrage Python: ${error.message}`);
                return res.status(500).json({
                    success: false,
                    error: 'Erreur démarrage serveur Python',
                    message: error.message
                });
            }
            
            if (stderr) {
                console.error(`⚠️ Stderr Python: ${stderr}`);
            }
            
            console.log(`✅ Sortie Python: ${stdout}`);
            
            res.json({
                success: true,
                message: 'Serveur Python démarré',
                output: stdout
            });
        });
    } catch (error) {
        console.error('❌ Erreur démarrage serveur Python:', error);
        res.status(500).json({
            success: false,
            error: 'Erreur interne',
            message: error.message
        });
    }
});

// 13. Vérifier l'état du serveur Python
router.get('/python-status', async (req, res) => {
    try {
        // Tenter de contacter le serveur Python
        const response = await axios.get(`${PYTHON_SERVER_URL}/api/health`, {
            timeout: 5000
        });
        
        res.json({
            success: true,
            pythonServer: 'running',
            status: response.data
        });
    } catch (error) {
        if (error.code === 'ECONNREFUSED') {
            res.json({
                success: false,
                pythonServer: 'stopped',
                message: 'Serveur Python non démarré (port 5003)'
            });
        } else {
            res.json({
                success: false,
                pythonServer: 'error',
                message: error.message
            });
        }
    }
});

// ============================================
// ROUTES DE DEBUG
// ============================================

// 14. Tester une requête spécifique au BOAMP
router.post('/test-boamp-query', async (req, res) => {
    try {
        const { query, date_debut, date_fin } = req.body;
        
        const response = await axios.get(`${PYTHON_SERVER_URL}/api/test-query`, {
            params: { query, date_debut, date_fin },
            timeout: 60000
        });
        
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// 15. Obtenir les logs du scraper Python
router.get('/logs', async (req, res) => {
    try {
        const fs = require('fs');
        const logPath = path.join(__dirname, '../backend/scripts/scraper.log');
        
        if (fs.existsSync(logPath)) {
            const logs = fs.readFileSync(logPath, 'utf8');
            const lines = logs.split('\n').reverse().slice(0, 100); // 100 dernières lignes
            
            res.json({
                success: true,
                logs: lines,
                totalLines: logs.split('\n').length
            });
        } else {
            res.json({
                success: false,
                message: 'Fichier log non trouvé'
            });
        }
    } catch (error) {
        console.error('❌ Erreur lecture logs:', error);
        res.status(500).json({
            success: false,
            error: 'Erreur lecture logs',
            message: error.message
        });
    }
});

// 16. Tester un mot-clé spécifique
router.post('/test-keyword', async (req, res) => {
    try {
        const { keyword, date_debut, date_fin } = req.body;
        
        if (!keyword) {
            return res.status(400).json({
                success: false,
                error: 'Mot-clé requis'
            });
        }
        
        // Construire la requête BOAMP
        const words = keyword.split(' ');
        const query = words.length > 1 
            ? words.map(word => `"${word}"`).join(' OR ')
            : `"${keyword}"`;
        
        const testPayload = {
            query,
            date_debut: date_debut || '2024-01-01',
            date_fin: date_fin || '2024-12-31'
        };
        
        console.log(`🔍 Test mot-clé: "${keyword}" -> ${query}`);
        
        // Utiliser l'endpoint de test ou directement l'API BOAMP
        const response = await axios.post(
            `${PYTHON_SERVER_URL}/api/test-query`,
            testPayload,
            { timeout: 60000 }
        );
        
        res.json({
            success: true,
            keyword,
            query,
            results: response.data
        });
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// ============================================
// MIDDLEWARE DE GESTION D'ERREURS
// ============================================

// Middleware pour routes non trouvées
router.use((req, res) => {
    res.status(404).json({
        success: false,
        error: 'Route non trouvée',
        message: `La route ${req.method} ${req.originalUrl} n'existe pas dans l'API BOAMP`
    });
});

// Middleware pour erreurs globales
router.use((error, req, res, next) => {
    console.error('❌ Erreur globale route BOAMP:', error);
    
    res.status(500).json({
        success: false,
        error: 'Erreur interne serveur',
        message: process.env.NODE_ENV === 'development' ? error.message : 'Une erreur est survenue'
    });
});

module.exports = router;