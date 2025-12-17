// server.js - VERSION CORRIGÉE avec Authentification
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const helmet = require('helmet');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const { createProxyMiddleware } = require('http-proxy-middleware');

require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5000;

// ==================== IMPORTATION DES ROUTES ====================
const authRoutes = require('./routes/auth');
const userRoutes = require('./routes/users');
const tunepsRoutes = require('./routes/tuneps');
const boampRoutes = require('./routes/routesboamp');

// ==================== REACT FRONTEND ====================
const REACT_BUILD_DIR = path.join(__dirname, '..', 'auth-frontend', 'build');
const reactBuildExists = fs.existsSync(REACT_BUILD_DIR);

// ==================== MIDDLEWARE ====================
app.use(helmet({ contentSecurityPolicy: false }));
app.use(cors({
  origin: ['http://localhost:3000', 'http://localhost:3001', 'http://127.0.0.1:3000', 'http://localhost:5000', 'http://localhost:5003', 'http://localhost:5006'],
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: true
}));
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// ==================== MONGODB ====================
const MONGODB_URI = process.env.MONGO_URI || 'mongodb://localhost:27017/marmoucha';
mongoose.connect(MONGODB_URI)
  .then(() => console.log('✅ MongoDB connected to marmoucha database'))
  .catch(err => {
    console.error('❌ MongoDB connection error:', err.message);
    console.log('⚠️ Continuing without MongoDB...');
  });

// ==================== ROUTES ====================
// Routes d'authentification
app.use('/api/auth', authRoutes);
app.use('/api/users', userRoutes);

// Routes pour les scrapers
app.use('/api/tuneps', tunepsRoutes);
app.use('/api/boamp', boampRoutes);

// PNUD : Proxy vers le serveur Flask
app.use('/api/pnud', createProxyMiddleware({
  target: 'http://localhost:5006',
  changeOrigin: true,
  pathRewrite: { '^/api/pnud': '' },
  onProxyReq: (proxyReq, req, res) => {
    console.log(`➡️  Proxy PNUD: ${req.method} ${req.originalUrl} → ${proxyReq.path}`);
  },
  onProxyRes: (proxyRes, req, res) => {
    console.log(`⬅️  Réponse PNUD: ${proxyRes.statusCode} ${req.originalUrl}`);
  },
  onError: (err, req, res) => {
    console.error('❌ Proxy PNUD error:', err.message);
    res.status(502).json({
      success: false,
      message: 'Scraper PNUD non disponible',
      error: err.message
    });
  }
}));

// HAICOP : Proxy vers le serveur Flask
app.use('/api/haicop', createProxyMiddleware({
  target: 'http://localhost:5009',
  changeOrigin: true,
  pathRewrite: { '^/api/haicop': '' },
  onError: (err, req, res) => {
    console.error('❌ Proxy HAICOP error:', err.message);
    res.status(502).json({
      success: false,
      message: 'Scraper HAICOP non disponible',
      error: err.message
    });
  }
}));

// BANQUE MONDIALE : Proxy
app.use('/api/banque', createProxyMiddleware({
  target: 'http://localhost:5010',
  changeOrigin: true,
  pathRewrite: { '^/api/banque': '' },
  onError: (err, req, res) => {
    console.error('❌ Proxy BANQUE error:', err.message);
    res.status(502).json({
      success: false,
      message: 'Scraper BANQUE MONDIALE non disponible',
      error: err.message
    });
  }
}));

// ==================== SCRAPERS PYTHON ====================
let pythonProcess = null;
let pnudPythonProcess = null;
let haicopPythonProcess = null;
let banquePythonProcess = null;

function startBoampPythonScraper() {
  if (pythonProcess && !pythonProcess.killed) {
    console.log(`✅ Scraper BOAMP déjà en cours (PID: ${pythonProcess.pid})`);
    return;
  }

  const pythonScriptPath = path.join(__dirname, 'scripts', 'scraper.py');
  if (!fs.existsSync(pythonScriptPath)) {
    console.error('❌ scraper.py non trouvé !');
    return;
  }

  console.log('🚀 Démarrage automatique du scraper Python BOAMP...');
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  pythonProcess = spawn(pythonCmd, [pythonScriptPath], {
    cwd: path.dirname(pythonScriptPath),
    stdio: ['ignore', 'pipe', 'pipe']
  });

  pythonProcess.stdout.on('data', (data) => process.stdout.write(`[BOAMP] ${data.toString().trim()}\n`));
  pythonProcess.stderr.on('data', (data) => process.stderr.write(`[BOAMP ERR] ${data.toString().trim()}\n`));

  pythonProcess.on('close', (code) => {
    console.log(`❌ Scraper BOAMP terminé avec code ${code}`);
    pythonProcess = null;
    if (code !== 0) setTimeout(startBoampPythonScraper, 5000);
  });

  pythonProcess.on('error', (err) => console.error('❌ Erreur lancement BOAMP :', err.message));
  console.log(`✅ Scraper BOAMP lancé (PID: ${pythonProcess.pid})`);
}

function startPnudPythonScraper() {
  if (pnudPythonProcess && !pnudPythonProcess.killed) {
    console.log(`✅ Scraper PNUD déjà en cours (PID: ${pnudPythonProcess.pid})`);
    return;
  }

  const scriptPath = path.join(__dirname, 'scripts', 'pnud.py');
  
  if (!fs.existsSync(scriptPath)) {
    console.error('❌ pnud.py non trouvé !');
    return;
  }

  console.log('🚀 Démarrage du scraper PNUD...');
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  pnudPythonProcess = spawn(pythonCmd, [scriptPath], {
    cwd: path.dirname(scriptPath),
    stdio: ['pipe', 'pipe', 'pipe']
  });

  pnudPythonProcess.stdout.on('data', (data) => {
    const output = data.toString().trim();
    console.log(`[PNUD STDOUT] ${output}`);
    fs.appendFileSync('pnud_server.log', `[${new Date().toISOString()}] ${output}\n`);
  });

  pnudPythonProcess.stderr.on('data', (data) => {
    const output = data.toString().trim();
    console.error(`[PNUD STDERR] ${output}`);
    fs.appendFileSync('pnud_error.log', `[${new Date().toISOString()}] ${output}\n`);
  });

  pnudPythonProcess.on('close', (code) => {
    console.log(`❌ Scraper PNUD terminé avec code ${code}`);
    pnudPythonProcess = null;
    if (code !== 0) setTimeout(startPnudPythonScraper, 5000);
  });

  console.log(`✅ Scraper PNUD lancé (PID: ${pnudPythonProcess.pid})`);
}

function startHaicopPythonScraper() {
  if (haicopPythonProcess && !haicopPythonProcess.killed) {
    console.log(`✅ Scraper HAICOP déjà en cours (PID: ${haicopPythonProcess.pid})`);
    return;
  }

  const scriptPath = path.join(__dirname, 'scripts', 'haicop.py');

  if (!fs.existsSync(scriptPath)) {
    console.error('❌ haicop.py non trouvé !');
    return;
  }

  console.log('🚀 Démarrage du scraper HAICOP...');
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  haicopPythonProcess = spawn(pythonCmd, [scriptPath], {
    cwd: path.dirname(scriptPath),
    stdio: ['pipe', 'pipe', 'pipe']
  });

  haicopPythonProcess.stdout.on('data', (data) => {
    const output = data.toString().trim();
    console.log(`[HAICOP STDOUT] ${output}`);
    fs.appendFileSync('haicop_server.log', `[${new Date().toISOString()}] ${output}\n`);
  });

  haicopPythonProcess.stderr.on('data', (data) => {
    const output = data.toString().trim();
    console.error(`[HAICOP STDERR] ${output}`);
    fs.appendFileSync('haicop_error.log', `[${new Date().toISOString()}] ${output}\n`);
  });

  haicopPythonProcess.on('close', (code) => {
    console.log(`❌ Scraper HAICOP terminé avec code ${code}`);
    haicopPythonProcess = null;
    if (code !== 0) setTimeout(startHaicopPythonScraper, 5000);
  });

  console.log(`✅ Scraper HAICOP lancé (PID: ${haicopPythonProcess.pid})`);
}

function startBanquePythonScraper() {
  if (banquePythonProcess && !banquePythonProcess.killed) {
    console.log(`✅ Scraper BANQUE déjà en cours (PID: ${banquePythonProcess.pid})`);
    return;
  }

  const scriptPath = path.join(__dirname, 'scripts', 'banque_flask.py');

  if (!fs.existsSync(scriptPath)) {
    console.error('❌ banque_flask.py non trouvé !');
    return;
  }

  console.log('🚀 Démarrage du scraper BANQUE MONDIALE...');
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  banquePythonProcess = spawn(pythonCmd, [scriptPath], {
    cwd: path.dirname(scriptPath),
    stdio: ['pipe', 'pipe', 'pipe']
  });

  banquePythonProcess.stdout.on('data', (data) => {
    const output = data.toString().trim();
    console.log(`[BANQUE STDOUT] ${output}`);
    fs.appendFileSync('banque_server.log', `[${new Date().toISOString()}] ${output}\n`);
  });

  banquePythonProcess.stderr.on('data', (data) => {
    const output = data.toString().trim();
    console.error(`[BANQUE STDERR] ${output}`);
    fs.appendFileSync('banque_error.log', `[${new Date().toISOString()}] ${output}\n`);
  });

  banquePythonProcess.on('close', (code) => {
    console.log(`❌ Scraper BANQUE terminé avec code ${code}`);
    banquePythonProcess = null;
    if (code !== 0) setTimeout(startBanquePythonScraper, 5000);
  });

  console.log(`✅ Scraper BANQUE lancé (PID: ${banquePythonProcess.pid})`);
}

// ==================== HEALTH & INFO ====================
app.get('/health', async (req, res) => {
  const health = {
    node: 'healthy',
    timestamp: new Date().toISOString(),
    mongodb: mongoose.connection.readyState === 1 ? 'connected' : 'disconnected',
    database: 'marmoucha',
    frontend: reactBuildExists ? 'build found' : 'build not found',
    services: {
      auth: 'available',
      users: 'available',
      tuneps: 'available',
      boamp: pythonProcess ? `running (PID: ${pythonProcess.pid})` : 'not started',
      pnud: pnudPythonProcess ? `running (PID: ${pnudPythonProcess.pid})` : 'not started',
      haicop: haicopPythonProcess ? `running (PID: ${haicopPythonProcess.pid})` : 'not started',
      banque: banquePythonProcess ? `running (PID: ${banquePythonProcess.pid})` : 'not started'
    }
  };
  res.json(health);
});

app.get('/info', (req, res) => {
  res.json({
    name: 'Scraper API avec Authentification',
    version: '6.0.0',
    description: 'API complète avec authentification JWT et scrapers multiples',
    endpoints: {
      auth: {
        register: 'POST /api/auth/register',
        login: 'POST /api/auth/login'
      },
      users: {
        create: 'POST /api/users/create (ADMIN/SUPER_ADMIN)'
      },
      scrapers: {
        health: 'GET /health',
        tuneps_test: 'GET /api/tuneps/test',
        boamp_test: 'GET /api/boamp/test-python',
        pnud_scrape: 'POST /api/pnud/api/scrape',
        haicop_scrape: 'POST /api/haicop/api/scrape-tunisie',
        banque_scrape: 'POST /api/banque/api/scrape'
      }
    }
  });
});

// ==================== SERVIR REACT ====================
if (reactBuildExists) {
  app.use(express.static(REACT_BUILD_DIR));
  app.get('*', (req, res) => {
    if (req.path.startsWith('/api')) {
      return res.status(404).json({ success: false, error: 'API route not found' });
    }
    res.sendFile(path.join(REACT_BUILD_DIR, 'index.html'));
  });
  console.log(`✅ React build trouvé : ${REACT_BUILD_DIR}`);
} else {
  app.get('/', (req, res) => {
    res.send(`
      <!DOCTYPE html>
      <html lang="fr">
      <head>
        <meta charset="UTF-8">
        <title>API Scraper avec Authentification</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
          .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
          h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
          .endpoints { background: #f1f8ff; padding: 20px; border-radius: 8px; margin: 20px 0; }
          code { background: #2c3e50; color: white; padding: 2px 6px; border-radius: 4px; }
          .btn { display: inline-block; padding: 10px 20px; margin: 10px 5px; background: #3498db; color: white; text-decoration: none; border-radius: 5px; }
        </style>
      </head>
      <body>
        <div class="container">
          <h1>🔐 API Scraper avec Authentification</h1>
          <p><strong>Serveur Node.js</strong> sur port ${PORT}</p>
          
          <div class="endpoints">
            <h3>🔑 Authentification</h3>
            <ul>
              <li><code>POST /api/auth/register</code> - Inscription utilisateur</li>
              <li><code>POST /api/auth/login</code> - Connexion</li>
              <li><code>POST /api/users/create</code> - Créer utilisateur (ADMIN)</li>
            </ul>
          </div>
          
          <div>
            <h3>⚡ Tester avec Postman</h3>
            <a href="/health" class="btn">Vérifier santé</a>
            <a href="/info" class="btn">Info API</a>
          </div>
        </div>
      </body>
      </html>
    `);
  });
}

// ==================== ERREURS ====================
app.use((req, res) => {
  console.error(`404 - ${req.method} ${req.originalUrl}`);
  res.status(404).json({ success: false, error: 'Route not found' });
});

app.use((err, req, res, next) => {
  console.error('Server error:', err);
  res.status(500).json({ success: false, error: 'Internal server error' });
});

// ==================== DÉMARRAGE ====================
app.listen(PORT, '0.0.0.0', async () => {
  console.log(`\n` + '='.repeat(80));
  console.log(`🚀 Serveur Node.js démarré → http://localhost:${PORT}`);
  console.log('='.repeat(80) + '\n');

  // Démarrer les scrapers Python
  startBoampPythonScraper();
  startPnudPythonScraper();
  startHaicopPythonScraper();
  startBanquePythonScraper();

  console.log(`
🎯 API AUTHENTIFICATION PRÊTE !

Endpoints:
• Register: POST http://localhost:${PORT}/api/auth/register
• Login: POST http://localhost:${PORT}/api/auth/login
• Créer user (ADMIN): POST http://localhost:${PORT}/api/users/create

📊 Ports actifs:
• Backend Node.js: ${PORT}
• BOAMP: 5003
• PNUD: 5006
• HAICOP: 5009
• BANQUE: 5010

  `);
});

// Gestion propre de l'arrêt
process.on('SIGINT', () => {
  console.log('\n⚠️ Arrêt du serveur demandé...');
  [pythonProcess, pnudPythonProcess, haicopPythonProcess, banquePythonProcess].forEach(proc => {
    if (proc) {
      console.log(`Arrêt PID: ${proc.pid}...`);
      proc.kill();
    }
  });
  process.exit(0);
});

module.exports = app;