// routes/tuneps_proxy.js - Proxy simple vers Flask Python TUNEPS
const express = require('express');
const router = express.Router();
const axios = require('axios');

// Configuration
const PYTHON_SERVER_URL = 'http://localhost:5001';
const PYTHON_API_TIMEOUT = 1800000; // 30 minutes

// Middleware pour gérer les erreurs axios
const handlePythonApiError = (error, res) => {
    console.error('❌ Erreur communication avec serveur Python TUNEPS:', error.message);

    if (error.code === 'ECONNREFUSED') {
        return res.status(503).json({
            success: false,
            error: 'Serveur Python TUNEPS non disponible',
            message: 'Le serveur Python (port 5001) n\'est pas démarré ou inaccessible'
        });
    }

    if (error.response) {
        return res.status(error.response.status).json({
            success: false,
            error: `Erreur serveur Python (${error.response.status})`,
            message: error.response.data?.error || error.response.statusText,
            details: error.response.data
        });
    }

    if (error.request) {
        return res.status(504).json({
            success: false,
            error: 'Timeout serveur Python',
            message: 'Le serveur Python n\'a pas répondu dans le délai imparti'
        });
    }

    return res.status(500).json({
        success: false,
        error: 'Erreur interne',
        message: error.message
    });
};

// ===== ROUTES PRINCIPALES =====

// Test
router.get('/test', async (req, res) => {
    try {
        const response = await axios.get(`${PYTHON_SERVER_URL}/api/test`, {
            timeout: 10000
        });
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// Status
router.get('/status', async (req, res) => {
    try {
        const response = await axios.get(`${PYTHON_SERVER_URL}/api/status`, {
            timeout: 10000
        });
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// Scraping
router.post('/scrape', async (req, res) => {
    try {
        console.log('🚀 Lancement scraping TUNEPS');
        const response = await axios.post(`${PYTHON_SERVER_URL}/api/scrape`, req.body, {
            timeout: PYTHON_API_TIMEOUT
        });
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// Obtenir pending
router.get('/pending', async (req, res) => {
    try {
        const { page = 1, limit = 10 } = req.query;
        const response = await axios.get(`${PYTHON_SERVER_URL}/api/pending`, {
            params: { page, limit },
            timeout: 30000
        });
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// Obtenir tenders (validées)
router.get('/tenders', async (req, res) => {
    try {
        const response = await axios.get(`${PYTHON_SERVER_URL}/api/tenders`, {
            timeout: 30000
        });
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// Valider une offre
router.post('/validate/:reference', async (req, res) => {
    try {
        const { reference } = req.params;
        console.log(`✅ Validation offre TUNEPS: ${reference}`);

        const response = await axios.post(
            `${PYTHON_SERVER_URL}/api/validate/${reference}`,
            req.body,
            { timeout: 30000 }
        );
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// Mettre à jour une offre
router.post('/update/:reference', async (req, res) => {
    try {
        const { reference } = req.params;
        const response = await axios.post(
            `${PYTHON_SERVER_URL}/api/update/${reference}`,
            req.body,
            { timeout: 30000 }
        );
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// Supprimer une offre pending
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

// Supprimer une offre validée
router.delete('/tenders/delete/:reference', async (req, res) => {
    try {
        const { reference } = req.params;
        const response = await axios.delete(
            `${PYTHON_SERVER_URL}/api/tenders/delete/${reference}`,
            { timeout: 30000 }
        );
        res.json(response.data);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// Download PDF
router.get('/download_pdf/:filename', async (req, res) => {
    try {
        const { filename } = req.params;
        const response = await axios.get(
            `${PYTHON_SERVER_URL}/api/download_pdf/${filename}`,
            { responseType: 'stream', timeout: 60000 }
        );
        response.data.pipe(res);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// Download Image
router.get('/download_image/:filename', async (req, res) => {
    try {
        const { filename } = req.params;
        const response = await axios.get(
            `${PYTHON_SERVER_URL}/api/download_image/${filename}`,
            { responseType: 'stream', timeout: 60000 }
        );
        response.data.pipe(res);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

// Download Excel
router.get('/download_excel/:filename', async (req, res) => {
    try {
        const { filename } = req.params;
        const response = await axios.get(
            `${PYTHON_SERVER_URL}/api/download_excel/${filename}`,
            { responseType: 'stream', timeout: 60000 }
        );
        response.data.pipe(res);
    } catch (error) {
        handlePythonApiError(error, res);
    }
});

module.exports = router;
