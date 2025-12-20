// routes/pnud.js - Proxy vers le scraper Python PNUD (port 5006)
const express = require('express');
const router = express.Router();
const { createProxyMiddleware } = require('http-proxy-middleware');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Configuration du proxy vers le serveur Python PNUD
const PNUD_PYTHON_PORT = 5006;
const PNUD_API_TARGET = `http://localhost:${PNUD_PYTHON_PORT}/api`;

// Variable globale pour le process Python
let pnudPythonProcess = null;

// Fonction pour lancer automatiquement pnud.py
function startPnudPythonScraper() {
  if (pnudPythonProcess && !pnudPythonProcess.killed) {
    console.log(`✅ Scraper PNUD Python déjà en cours (PID: ${pnudPythonProcess.pid})`);
    return;
  }

  const scriptPath = path.join(__dirname, '..', 'scripts', 'pnud.py');

  if (!fs.existsSync(scriptPath)) {
    console.error('❌ pnud.py non trouvé à:', scriptPath);
    return;
  }

  console.log('🚀 Démarrage automatique du scraper PNUD Python (port 5006)...');

  pnudPythonProcess = spawn('python', [scriptPath], {
    cwd: path.dirname(scriptPath),
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: false,
    windowsHide: true
  });

  pnudPythonProcess.stdout.on('data', (data) => {
    process.stdout.write(`[PNUD PYTHON] ${data.toString().trim()}\n`);
  });

  pnudPythonProcess.stderr.on('data', (data) => {
    process.stderr.write(`[PNUD ERROR] ${data.toString().trim()}\n`);
  });

  pnudPythonProcess.on('close', (code) => {
    console.log(`❌ Scraper PNUD Python terminé (code ${code})`);
    pnudPythonProcess = null;
    if (code !== 0) {
      console.log('🔄 Redémarrage dans 5s...');
      setTimeout(startPnudPythonScraper, 5000);
    }
  });

  pnudPythonProcess.on('error', (err) => {
    console.error('❌ Erreur lancement PNUD Python:', err.message);
  });

  console.log(`✅ PNUD Python lancé (PID: ${pnudPythonProcess.pid})`);
}

// Proxy pour toutes les routes /api/*
router.use('/api', createProxyMiddleware({
  target: PNUD_API_TARGET,
  changeOrigin: true,
  pathRewrite: { '^/api/pnud/api': '/api' },
  onProxyReq: (proxyReq, req, res) => {
    console.log(`➡️  Proxy PNUD: ${req.method} ${req.url}`);
  },
  onError: (err, req, res) => {
    console.error('❌ Proxy PNUD error:', err.message);
    if (err.code === 'ECONNREFUSED') {
      res.status(502).json({
        success: false,
        message: 'Scraper PNUD non démarré. Tentative de démarrage...',
        hint: 'Le serveur Python va démarrer automatiquement'
      });
      startPnudPythonScraper(); // Auto-start si pas lancé
    }
  }
}));

// Route de test directe
router.get('/test', (req, res) => {
  res.json({
    success: true,
    message: 'Route PNUD.js fonctionne !',
    python_status: pnudPythonProcess ? `running (PID: ${pnudPythonProcess.pid})` : 'not started',
    proxy_target: PNUD_API_TARGET
  });
});

// Health check avec lancement auto
router.get('/health', (req, res) => {
  startPnudPythonScraper(); // Force start si besoin
  res.json({
    service: 'PNUD Proxy',
    python_running: !!pnudPythonProcess,
    pid: pnudPythonProcess?.pid || null,
    port: PNUD_PYTHON_PORT
  });
});

module.exports = { router, startPnudPythonScraper };