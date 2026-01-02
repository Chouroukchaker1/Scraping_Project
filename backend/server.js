// server.js - VERSION POSTGRESQL COMPLÈTE
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const { createProxyMiddleware } = require('http-proxy-middleware');
const axios = require('axios');

require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 8080;

// ==================== IMPORTATION DES ROUTES ====================
const authRoutes = require('./routes/auth');
const userRoutes = require('./routes/users');
const tunepsRoutes = require('./routes/tuneps');  // ✅ UTILISER tuneps.js avec PostgreSQL au lieu de tuneps_proxy.js
const boampRoutes = require('./routes/routesboamp');

// ==================== REACT FRONTEND ====================
const REACT_BUILD_DIR = path.join(__dirname, '..', 'auth-frontend', 'build');
const reactBuildExists = fs.existsSync(REACT_BUILD_DIR);

// ==================== MIDDLEWARE ====================
app.use(helmet({ contentSecurityPolicy: false }));
app.use(cors({
  origin: ['http://localhost:3000', 'http://localhost:3001', 'http://127.0.0.1:3000', 'http://localhost:5000', 'http://localhost:5003', 'http://localhost:5006', 'http://localhost:8080'],
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: true
}));
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

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
  pathRewrite: { '^/api/pnud': '/api' },  // ✅ Fixed: was '' now '/api'
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

// HAICOP SCRAPE ENDPOINT - Must be BEFORE the proxy to intercept POST /scrape
app.post('/api/haicop/api/scrape-tunisie', async (req, res) => {
  try {
    const axios = require('axios');
    console.log('📤 Forwarding HAICOP scrape-tunisie request:', req.body);

    const response = await axios.post('http://localhost:5011/api/scrape-tunisie', req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 120000  // 2 minutes pour le scraping
    });

    console.log('✅ HAICOP scrape-tunisie response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ HAICOP scrape-tunisie error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// HAICOP VALIDATE ENDPOINT
app.post('/api/haicop/api/validate/:reference', async (req, res) => {
  try {
    const axios = require('axios');
    const reference = req.params.reference;
    console.log('📤 Forwarding HAICOP validate request:', reference);

    const response = await axios.post(`http://localhost:5011/api/validate/${encodeURIComponent(reference)}`, req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000
    });

    console.log('✅ HAICOP validate response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ HAICOP validate error:', error.message);
    res.status(500).json({
      success: false,
      error: error.response?.data?.message || error.message
    });
  }
});

// HAICOP : Proxy pour les autres endpoints
app.use('/api/haicop', createProxyMiddleware({
  target: 'http://localhost:5011',
  changeOrigin: true,
  pathRewrite: { '^/api/haicop': '/api' },
  onError: (err, req, res) => {
    console.error('❌ Proxy HAICOP error:', err.message);
    res.status(502).json({
      success: false,
      message: 'Scraper HAICOP non disponible',
      error: err.message
    });
  }
}));

// BANQUE MONDIALE SCRAPE ENDPOINT - Must be BEFORE the proxy to intercept POST /scrape
app.post('/api/banque/api/scrape', async (req, res) => {
  try {
    const axios = require('axios');
    console.log('📤 Forwarding BANQUE scrape request:', req.body);

    const response = await axios.post('http://localhost:5010/api/scrape', req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 120000  // 2 minutes pour le scraping
    });

    console.log('✅ BANQUE scrape response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ BANQUE scrape error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// BANQUE MONDIALE : Proxy for other endpoints
app.use('/api/banque', createProxyMiddleware({
  target: 'http://localhost:5010',
  changeOrigin: true,
  pathRewrite: { '^/api/banque': '/api' },
  onError: (err, req, res) => {
    console.error('❌ Proxy BANQUE error:', err.message);
    res.status(502).json({
      success: false,
      message: 'Scraper BANQUE MONDIALE non disponible',
      error: err.message
    });
  }
}));

// TUNEPS AO SCRAPE ENDPOINT - Must be BEFORE the proxy to intercept POST /scrape
app.post('/api/tuneps_ao/api/scrape', async (req, res) => {
  try {
    const axios = require('axios');
    console.log('📤 Forwarding TUNEPS AO scrape request:', req.body);

    const response = await axios.post('http://localhost:5005/api/scrape', req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 5000
    });

    console.log('✅ TUNEPS AO scrape response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ TUNEPS AO scrape error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// TUNEPS AO VALIDATE ENDPOINT - Must be BEFORE the proxy to intercept
app.post('/api/tuneps_ao/api/validate/:reference', async (req, res) => {
  try {
    const axios = require('axios');
    const reference = req.params.reference;
    console.log('📤 Forwarding TUNEPS AO validate request:', reference);

    const response = await axios.post(`http://localhost:5005/api/validate/${encodeURIComponent(reference)}`, req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 90000  // 90 secondes pour l'API
    });

    console.log('✅ TUNEPS AO validate response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ TUNEPS AO validate error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// TUNEPS AO : Proxy vers le serveur Flask (port 5005) for other endpoints
app.use('/api/tuneps_ao', createProxyMiddleware({
  target: 'http://localhost:5005',
  changeOrigin: true,
  pathRewrite: { '^/api/tuneps_ao': '/api' },  // ✅ Fixed: was '' now '/api'
  timeout: 300000, // 5 minutes timeout for long scraping operations
  proxyTimeout: 300000,
  onProxyReq: (proxyReq, req, res) => {
    console.log(`➡️  Proxy TUNEPS AO: ${req.method} ${req.originalUrl} → ${proxyReq.path}`);

    // Fix Content-Type and body for POST requests
    if (req.method === 'POST' && req.body) {
      const bodyData = JSON.stringify(req.body);
      proxyReq.setHeader('Content-Type', 'application/json');
      proxyReq.setHeader('Content-Length', Buffer.byteLength(bodyData));
      proxyReq.write(bodyData);
      console.log(`📤 Body forwarded: ${bodyData}`);
    }
  },
  onProxyRes: (proxyRes, req, res) => {
    console.log(`⬅️  Réponse TUNEPS AO: ${proxyRes.statusCode} ${req.originalUrl}`);
  },
  onError: (err, req, res) => {
    console.error('❌ Proxy TUNEPS AO error:', err.message);
    res.status(502).json({
      success: false,
      message: 'Scraper TUNEPS AO non disponible',
      error: err.message
    });
  }
}));

// ARMP VALIDATE ENDPOINT - Must be BEFORE the proxy to intercept POST /validate
app.post('/api/armp/api/validate/:reference', async (req, res) => {
  try {
    const axios = require('axios');
    const reference = req.params.reference;
    console.log('📤 Forwarding ARMP validate request:', reference);

    const response = await axios.post(`http://localhost:5007/api/validate/${encodeURIComponent(reference)}`, req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000
    });

    console.log('✅ ARMP validate response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ ARMP validate error:', error.message);
    res.status(500).json({
      success: false,
      error: error.response?.data?.message || error.message
    });
  }
});

// ARMP : Proxy for other endpoints
app.use('/api/armp', createProxyMiddleware({
  target: 'http://localhost:5007',
  changeOrigin: true,
  pathRewrite: { '^/api/armp': '' },
  onError: (err, req, res) => {
    console.error('❌ Proxy ARMP error:', err.message);
    res.status(502).json({
      success: false,
      message: 'Scraper ARMP non disponible',
      error: err.message
    });
  }
}));

// BENIN : Proxy vers le serveur Flask
app.use('/api/benin', createProxyMiddleware({
  target: 'http://localhost:5012',
  changeOrigin: true,
  pathRewrite: { '^/api/benin': '' },
  onError: (err, req, res) => {
    console.error('❌ Proxy BENIN error:', err.message);
    res.status(502).json({
      success: false,
      message: 'Scraper BENIN non disponible',
      error: err.message
    });
  }
}));

// EXPERTISE FRANCE SCRAPE ENDPOINT - Must be BEFORE the proxy
app.post('/api/expertise/api/scrape', async (req, res) => {
  try {
    const axios = require('axios');
    console.log('📤 Forwarding EXPERTISE scrape request:', req.body);

    const response = await axios.post('http://localhost:5013/api/scrape', req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 120000
    });

    console.log('✅ EXPERTISE scrape response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ EXPERTISE scrape error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// EXPERTISE FRANCE VALIDATE ENDPOINT
app.post('/api/expertise/api/validate/:offer_id', async (req, res) => {
  try {
    const axios = require('axios');
    const offer_id = req.params.offer_id;
    console.log('📤 Forwarding EXPERTISE validate request:', offer_id);

    const response = await axios.post(`http://localhost:5013/api/validate/${encodeURIComponent(offer_id)}`, req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000
    });

    console.log('✅ EXPERTISE validate response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ EXPERTISE validate error:', error.message);
    res.status(500).json({
      success: false,
      error: error.response?.data?.message || error.message
    });
  }
});

// EXPERTISE FRANCE : Proxy for other endpoints
app.use('/api/expertise', createProxyMiddleware({
  target: 'http://localhost:5013',
  changeOrigin: true,
  pathRewrite: { '^/api/expertise': '' },
  onError: (err, req, res) => {
    console.error('❌ Proxy EXPERTISE error:', err.message);
    res.status(502).json({
      success: false,
      message: 'Scraper EXPERTISE FRANCE non disponible',
      error: err.message
    });
  }
}));

// GIZ SCRAPE ENDPOINT - Must be BEFORE the proxy
app.post('/api/giz/api/scrape', async (req, res) => {
  try {
    const axios = require('axios');
    console.log('📤 Forwarding GIZ scrape request:', req.body);

    const response = await axios.post('http://localhost:5014/api/scrape', req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 120000
    });

    console.log('✅ GIZ scrape response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ GIZ scrape error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// GIZ : Proxy for other endpoints
app.use('/api/giz', createProxyMiddleware({
  target: 'http://localhost:5014',
  changeOrigin: true,
  pathRewrite: { '^/api/giz': '' },
  onError: (err, req, res) => {
    console.error('❌ Proxy GIZ error:', err.message);
    res.status(502).json({
      success: false,
      message: 'Scraper GIZ non disponible',
      error: err.message
    });
  }
}));

// RELIEF: Custom endpoints
app.post('/api/relief/api/scrape', async (req, res) => {
  try {
    const axios = require('axios');
    console.log('📤 Forwarding RELIEF scrape request:', req.body);

    const response = await axios.post('http://localhost:5015/api/scrape', req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 120000
    });

    console.log('✅ RELIEF scrape response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ RELIEF scrape error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/relief/api/validate/:reference', async (req, res) => {
  try {
    const axios = require('axios');
    const reference = req.params.reference;
    console.log('📤 Forwarding RELIEF validate request:', reference);

    const response = await axios.post(`http://localhost:5015/api/validate/${encodeURIComponent(reference)}`, req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000
    });

    console.log('✅ RELIEF validate response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ RELIEF validate error:', error.message);
    res.status(500).json({
      success: false,
      error: error.response?.data?.message || error.message
    });
  }
});

app.post('/api/relief/api/delete_all', async (req, res) => {
  try {
    const axios = require('axios');
    console.log('📤 Forwarding RELIEF delete_all request');

    const response = await axios.post('http://localhost:5015/api/delete_all', req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 10000
    });

    console.log('✅ RELIEF delete_all response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ RELIEF delete_all error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// RELIEF: Proxy pour les autres endpoints
app.use('/api/relief', createProxyMiddleware({
  target: 'http://localhost:5015',
  changeOrigin: true,
  pathRewrite: { '^/api/relief': '/api' },
  onError: (err, req, res) => {
    console.error('❌ Proxy RELIEF error:', err.message);
    res.status(502).json({
      success: false,
      message: 'Scraper RELIEF non disponible',
      error: err.message
    });
  }
}));

// MEDIACONGO: Custom endpoints
app.post('/api/mediacongo/api/scrape', async (req, res) => {
  try {
    const axios = require('axios');
    console.log('📤 Forwarding MEDIACONGO scrape request:', req.body);

    const response = await axios.post('http://localhost:5016/api/scrape', req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 120000
    });

    console.log('✅ MEDIACONGO scrape response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ MEDIACONGO scrape error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/mediacongo/api/validate/:reference', async (req, res) => {
  try {
    const axios = require('axios');
    const reference = req.params.reference;
    console.log('📤 Forwarding MEDIACONGO validate request:', reference);

    const response = await axios.post(`http://localhost:5016/api/validate/${encodeURIComponent(reference)}`, req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000
    });

    console.log('✅ MEDIACONGO validate response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ MEDIACONGO validate error:', error.message);
    res.status(500).json({
      success: false,
      error: error.response?.data?.message || error.message
    });
  }
});

app.post('/api/mediacongo/api/delete_all', async (req, res) => {
  try {
    const axios = require('axios');
    console.log('📤 Forwarding MEDIACONGO delete_all request');

    const response = await axios.post('http://localhost:5016/api/delete_all', req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 10000
    });

    console.log('✅ MEDIACONGO delete_all response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ MEDIACONGO delete_all error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// MEDIACONGO: Proxy pour les autres endpoints
app.use('/api/mediacongo', createProxyMiddleware({
  target: 'http://localhost:5016',
  changeOrigin: true,
  pathRewrite: { '^/api/mediacongo': '/api' },
  onError: (err, req, res) => {
    console.error('❌ Proxy MEDIACONGO error:', err.message);
    res.status(502).json({
      success: false,
      message: 'Scraper MEDIACONGO non disponible',
      error: err.message
    });
  }
}));

// PPDA: Custom endpoints
app.post('/api/ppda/scrape', async (req, res) => {
  try {
    const axios = require('axios');
    console.log('📤 Forwarding PPDA scrape request:', req.body);

    const response = await axios.post('http://localhost:5017/scrape', req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 120000
    });

    console.log('✅ PPDA scrape response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ PPDA scrape error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/ppda/validate', async (req, res) => {
  try {
    const axios = require('axios');
    console.log('📤 Forwarding PPDA validate request');

    const response = await axios.post('http://localhost:5017/validate', req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000
    });

    console.log('✅ PPDA validate response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ PPDA validate error:', error.message);
    res.status(500).json({
      success: false,
      error: error.response?.data?.message || error.message
    });
  }
});

app.post('/api/ppda/delete_all', async (req, res) => {
  try {
    console.log('📤 Forwarding PPDA delete_all request');

    const response = await axios.post('http://localhost:5017/delete_all', req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000
    });

    console.log('✅ PPDA delete_all response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ PPDA delete_all error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// PPDA: Proxy pour les autres endpoints
app.use('/api/ppda', createProxyMiddleware({
  target: 'http://localhost:5017',
  changeOrigin: true,
  pathRewrite: { '^/api/ppda': '' },
  onError: (err, req, res) => {
    console.error('❌ Proxy PPDA error:', err.message);
    res.status(502).json({
      success: false,
      message: 'Scraper PPDA non disponible',
      error: err.message
    });
  }
}));

// NIGER: Routes POST explicites avec timeout étendu
app.post('/api/niger/scrape', async (req, res) => {
  console.log('🔔 ROUTE /api/niger/scrape APPELÉE!'); // DEBUG
  try {
    console.log('📤 Forwarding NIGER scrape request:', req.body);

    const response = await axios.post('http://localhost:5018/scrape', req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 1800000  // 30 minutes pour Selenium
    });

    console.log('✅ NIGER scrape response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ NIGER scrape error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/niger/validate', async (req, res) => {
  try {
    console.log('📤 Forwarding NIGER validate request');

    const response = await axios.post('http://localhost:5018/validate', req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000
    });

    console.log('✅ NIGER validate response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ NIGER validate error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/niger/delete_all', async (req, res) => {
  try {
    console.log('📤 Forwarding NIGER delete_all request');

    const response = await axios.post('http://localhost:5018/delete_all', req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000
    });

    console.log('✅ NIGER delete_all response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ NIGER delete_all error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// NIGER: Proxy pour les autres endpoints (GET)
app.use('/api/niger', createProxyMiddleware({
  target: 'http://localhost:5018',
  changeOrigin: true,
  pathRewrite: { '^/api/niger': '' },
  onError: (err, req, res) => {
    console.error('❌ Proxy NIGER error:', err.message);
    res.status(502).json({
      success: false,
      message: 'Scraper Niger non disponible',
      error: err.message
    });
  }
}));

// Somalia Jobs: Routes POST explicites
app.post('/api/somalia/scrape', async (req, res) => {
  try {
    const axios = require('axios');
    console.log('📤 Forwarding SOMALIA scrape request:', req.body);

    const response = await axios.post('http://localhost:5019/scrape', req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 300000  // 5 minutes pour Selenium
    });

    console.log('✅ SOMALIA scrape response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ SOMALIA scrape error:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/somalia/validate/:reference', async (req, res) => {
  try {
    const axios = require('axios');
    const reference = req.params.reference;
    console.log(`📤 Forwarding SOMALIA validate request for ${reference}`);

    const response = await axios.post(`http://localhost:5019/validate/${reference}`, req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000
    });

    console.log('✅ SOMALIA validate response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ SOMALIA validate error:', error.message);
    res.status(500).json({
      success: false,
      error: error.response?.data?.message || error.message
    });
  }
});

app.delete('/api/somalia/delete/:reference', async (req, res) => {
  try {
    const axios = require('axios');
    const reference = req.params.reference;
    console.log(`📤 Forwarding SOMALIA delete request for ${reference}`);

    const response = await axios.delete(`http://localhost:5019/delete/${reference}`, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000
    });

    console.log('✅ SOMALIA delete response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ SOMALIA delete error:', error.message);
    res.status(500).json({
      success: false,
      error: error.response?.data?.message || error.message
    });
  }
});

app.post('/api/somalia/delete_all', async (req, res) => {
  try {
    const axios = require('axios');
    console.log('📤 Forwarding SOMALIA delete_all request');

    const response = await axios.post('http://localhost:5019/delete_all', req.body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000
    });

    console.log('✅ SOMALIA delete_all response:', response.data);
    res.json(response.data);
  } catch (error) {
    console.error('❌ SOMALIA delete_all error:', error.message);
    res.status(500).json({
      success: false,
      error: error.response?.data?.message || error.message
    });
  }
});

// Somalia Jobs: Proxy pour les autres endpoints (GET)
app.use('/api/somalia', createProxyMiddleware({
  target: 'http://localhost:5019',
  changeOrigin: true,
  pathRewrite: { '^/api/somalia': '' },
  onError: (err, req, res) => {
    console.error('❌ Proxy SOMALIA error:', err.message);
    res.status(502).json({
      success: false,
      message: 'Scraper Somalia non disponible',
      error: err.message
    });
  }
}));

// ==================== SCRAPERS PYTHON ====================
let pythonProcess = null;
let pnudPythonProcess = null;
let haicopPythonProcess = null;
let banquePythonProcess = null;
let tunepsAoPythonProcess = null;
let armpPythonProcess = null;
let beninPythonProcess = null;
let expertisePythonProcess = null;
let gizPythonProcess = null;
let tunepsPythonProcess = null;
let reliefPythonProcess = null;
let mediacongoPythonProcess = null;
let ppdaPythonProcess = null;
let nigerPythonProcess = null;
let somaliaPythonProcess = null;

function startBoampPythonScraper() {
  if (pythonProcess && !pythonProcess.killed) {
    console.log(`✅ Scraper BOAMP déjà en cours (PID: ${pythonProcess.pid})`);
    return;
  }

  const pythonScriptPath = path.join(__dirname, 'scripts', 'boamp_official.py');
  if (!fs.existsSync(pythonScriptPath)) {
    console.error('❌ boamp_official.py non trouvé !');
    return;
  }

  console.log('🚀 Démarrage automatique du scraper Python BOAMP OFFICIEL...');
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

  const scriptPath = path.join(__dirname, 'scripts', 'banque_simple.py');
  if (!fs.existsSync(scriptPath)) {
    console.error('❌ banque_simple.py non trouvé !');
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

function startTunepsAoPythonScraper() {
  if (tunepsAoPythonProcess && !tunepsAoPythonProcess.killed) {
    console.log(`✅ Scraper TUNEPS AO déjà en cours (PID: ${tunepsAoPythonProcess.pid})`);
    return;
  }

  const scriptPath = path.join(__dirname, 'scripts', 'tuneps_ao.py');
  if (!fs.existsSync(scriptPath)) {
    console.error('❌ tuneps_ao.py non trouvé !');
    return;
  }

  console.log('🚀 Démarrage du scraper TUNEPS AO...');
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  tunepsAoPythonProcess = spawn(pythonCmd, [scriptPath], {
    cwd: path.join(__dirname, 'scripts'),
    stdio: ['pipe', 'pipe', 'pipe']  // Important : pipe pour capturer les logs
  });

  tunepsAoPythonProcess.stdout.on('data', (data) => {
    const output = data.toString().trim();
    console.log(`[TUNEPS AO STDOUT] ${output}`);
    fs.appendFileSync('tuneps_ao_server.log', `[${new Date().toISOString()}] ${output}\n`);
  });

  tunepsAoPythonProcess.stderr.on('data', (data) => {
    const output = data.toString().trim();
    console.error(`[TUNEPS AO STDERR] ${output}`);
    fs.appendFileSync('tuneps_ao_error.log', `[${new Date().toISOString()}] ${output}\n`);
  });

  tunepsAoPythonProcess.on('close', (code) => {
    console.log(`❌ Scraper TUNEPS AO terminé avec code ${code}`);
    tunepsAoPythonProcess = null;
    if (code !== 0) setTimeout(startTunepsAoPythonScraper, 5000);
  });

  tunepsAoPythonProcess.on('error', (err) => {
    console.error('❌ Erreur lancement TUNEPS AO:', err.message);
  });

  console.log(`✅ Scraper TUNEPS AO lancé (PID: ${tunepsAoPythonProcess.pid})`);
}

function startArmpPythonScraper() {
  if (armpPythonProcess && !armpPythonProcess.killed) {
    console.log(`✅ Scraper ARMP déjà en cours (PID: ${armpPythonProcess.pid})`);
    return;
  }

  const scriptPath = path.join(__dirname, 'scripts', 'armp.py');
  if (!fs.existsSync(scriptPath)) {
    console.error('❌ armp.py non trouvé !');
    return;
  }

  console.log('🚀 Démarrage du scraper ARMP...');
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  armpPythonProcess = spawn(pythonCmd, [scriptPath], {
    cwd: path.join(__dirname, 'scripts'),
    stdio: ['pipe', 'pipe', 'pipe']
  });

  armpPythonProcess.stdout.on('data', (data) => {
    const output = data.toString().trim();
    console.log(`[ARMP STDOUT] ${output}`);
    fs.appendFileSync('armp_server.log', `[${new Date().toISOString()}] ${output}\n`);
  });

  armpPythonProcess.stderr.on('data', (data) => {
    const output = data.toString().trim();
    console.error(`[ARMP STDERR] ${output}`);
    fs.appendFileSync('armp_error.log', `[${new Date().toISOString()}] ${output}\n`);
  });

  armpPythonProcess.on('close', (code) => {
    console.log(`❌ Scraper ARMP terminé avec code ${code}`);
    armpPythonProcess = null;
    if (code !== 0) setTimeout(startArmpPythonScraper, 5000);
  });

  console.log(`✅ Scraper ARMP lancé (PID: ${armpPythonProcess.pid})`);
}

function startTunepsPythonScraper() {
  if (tunepsPythonProcess && !tunepsPythonProcess.killed) {
    console.log(`✅ Scraper TUNEPS déjà en cours (PID: ${tunepsPythonProcess.pid})`);
    return;
  }

  const scriptPath = path.join(__dirname, 'scripts', 'tuneps.py');
  if (!fs.existsSync(scriptPath)) {
    console.error('❌ tuneps.py non trouvé !');
    return;
  }

  console.log('🚀 Démarrage du scraper TUNEPS...');
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  tunepsPythonProcess = spawn(pythonCmd, [scriptPath], {
    cwd: path.join(__dirname, 'scripts'),
    stdio: ['pipe', 'pipe', 'pipe']
  });

  tunepsPythonProcess.stdout.on('data', (data) => {
    console.log(`[TUNEPS STDOUT] ${data.toString().trim()}`);
  });

  tunepsPythonProcess.stderr.on('data', (data) => {
    console.error(`[TUNEPS STDERR] ${data.toString().trim()}`);
  });

  tunepsPythonProcess.on('close', (code) => {
    console.log(`❌ Scraper TUNEPS terminé avec code ${code}`);
    tunepsPythonProcess = null;
    if (code !== 0) setTimeout(startTunepsPythonScraper, 5000);
  });

  console.log(`✅ Scraper TUNEPS lancé (PID: ${tunepsPythonProcess.pid})`);
}

function startBeninPythonScraper() {
  if (beninPythonProcess && !beninPythonProcess.killed) {
    console.log(`✅ Scraper BENIN déjà en cours (PID: ${beninPythonProcess.pid})`);
    return;
  }

  const scriptPath = path.join(__dirname, 'scripts', 'benin.py');
  if (!fs.existsSync(scriptPath)) {
    console.error('❌ benin.py non trouvé !');
    return;
  }

  console.log('🚀 Démarrage du scraper BENIN...');
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  beninPythonProcess = spawn(pythonCmd, [scriptPath], {
    cwd: path.join(__dirname, 'scripts'),
    stdio: ['pipe', 'pipe', 'pipe']
  });

  beninPythonProcess.stdout.on('data', (data) => {
    console.log(`[BENIN STDOUT] ${data.toString().trim()}`);
  });

  beninPythonProcess.stderr.on('data', (data) => {
    console.error(`[BENIN STDERR] ${data.toString().trim()}`);
  });

  beninPythonProcess.on('close', (code) => {
    console.log(`❌ Scraper BENIN terminé avec code ${code}`);
    beninPythonProcess = null;
    if (code !== 0) setTimeout(startBeninPythonScraper, 5000);
  });

  console.log(`✅ Scraper BENIN lancé (PID: ${beninPythonProcess.pid})`);
}

function startExpertisePythonScraper() {
  if (expertisePythonProcess && !expertisePythonProcess.killed) {
    console.log(`✅ Scraper EXPERTISE déjà en cours (PID: ${expertisePythonProcess.pid})`);
    return;
  }

  const scriptPath = path.join(__dirname, 'scripts', 'expertise.py');
  if (!fs.existsSync(scriptPath)) {
    console.error('❌ expertise.py non trouvé !');
    return;
  }

  console.log('🚀 Démarrage du scraper EXPERTISE FRANCE...');
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  expertisePythonProcess = spawn(pythonCmd, [scriptPath], {
    cwd: path.join(__dirname, 'scripts'),
    stdio: ['pipe', 'pipe', 'pipe']
  });

  expertisePythonProcess.stdout.on('data', (data) => {
    console.log(`[EXPERTISE STDOUT] ${data.toString().trim()}`);
  });

  expertisePythonProcess.stderr.on('data', (data) => {
    console.error(`[EXPERTISE STDERR] ${data.toString().trim()}`);
  });

  expertisePythonProcess.on('close', (code) => {
    console.log(`❌ Scraper EXPERTISE terminé avec code ${code}`);
    expertisePythonProcess = null;
    if (code !== 0) setTimeout(startExpertisePythonScraper, 5000);
  });

  console.log(`✅ Scraper EXPERTISE lancé (PID: ${expertisePythonProcess.pid})`);
}

function startGizPythonScraper() {
  if (gizPythonProcess && !gizPythonProcess.killed) {
    console.log(`✅ Scraper GIZ déjà en cours (PID: ${gizPythonProcess.pid})`);
    return;
  }

  const scriptPath = path.join(__dirname, 'scripts', 'giz.py');
  if (!fs.existsSync(scriptPath)) {
    console.error('❌ giz.py non trouvé !');
    return;
  }

  console.log('🚀 Démarrage du scraper GIZ...');
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  gizPythonProcess = spawn(pythonCmd, [scriptPath], {
    cwd: path.join(__dirname, 'scripts'),
    stdio: ['pipe', 'pipe', 'pipe']
  });

  gizPythonProcess.stdout.on('data', (data) => {
    console.log(`[GIZ STDOUT] ${data.toString().trim()}`);
  });

  gizPythonProcess.stderr.on('data', (data) => {
    console.error(`[GIZ STDERR] ${data.toString().trim()}`);
  });

  gizPythonProcess.on('close', (code) => {
    console.log(`❌ Scraper GIZ terminé avec code ${code}`);
    gizPythonProcess = null;
    if (code !== 0) setTimeout(startGizPythonScraper, 5000);
  });

  console.log(`✅ Scraper GIZ lancé (PID: ${gizPythonProcess.pid})`);
}

function startReliefPythonScraper() {
  if (reliefPythonProcess && !reliefPythonProcess.killed) {
    console.log(`✅ Scraper RELIEF déjà en cours (PID: ${reliefPythonProcess.pid})`);
    return;
  }

  const scriptPath = path.join(__dirname, 'scripts', 'relief.py');
  if (!fs.existsSync(scriptPath)) {
    console.error('❌ relief.py non trouvé !');
    return;
  }

  console.log('🚀 Démarrage du scraper RELIEF...');
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  reliefPythonProcess = spawn(pythonCmd, [scriptPath], {
    cwd: path.join(__dirname, 'scripts'),
    stdio: ['pipe', 'pipe', 'pipe']
  });

  reliefPythonProcess.stdout.on('data', (data) => {
    console.log(`[RELIEF STDOUT] ${data.toString().trim()}`);
  });

  reliefPythonProcess.stderr.on('data', (data) => {
    console.error(`[RELIEF STDERR] ${data.toString().trim()}`);
  });

  reliefPythonProcess.on('close', (code) => {
    console.log(`❌ Scraper RELIEF terminé avec code ${code}`);
    reliefPythonProcess = null;
    if (code !== 0) setTimeout(startReliefPythonScraper, 5000);
  });

  console.log(`✅ Scraper RELIEF lancé (PID: ${reliefPythonProcess.pid})`);
}

function startMediaCongoPythonScraper() {
  if (mediacongoPythonProcess && !mediacongoPythonProcess.killed) {
    console.log(`✅ Scraper MEDIACONGO déjà en cours (PID: ${mediacongoPythonProcess.pid})`);
    return;
  }

  const scriptPath = path.join(__dirname, 'scripts', 'mediacongo.py');
  if (!fs.existsSync(scriptPath)) {
    console.error('❌ mediacongo.py non trouvé !');
    return;
  }

  console.log('🚀 Démarrage du scraper MEDIACONGO...');
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  mediacongoPythonProcess = spawn(pythonCmd, [scriptPath], {
    cwd: path.join(__dirname, 'scripts'),
    stdio: ['pipe', 'pipe', 'pipe']
  });

  mediacongoPythonProcess.stdout.on('data', (data) => {
    console.log(`[MEDIACONGO STDOUT] ${data.toString().trim()}`);
  });

  mediacongoPythonProcess.stderr.on('data', (data) => {
    console.error(`[MEDIACONGO STDERR] ${data.toString().trim()}`);
  });

  mediacongoPythonProcess.on('close', (code) => {
    console.log(`❌ Scraper MEDIACONGO terminé avec code ${code}`);
    mediacongoPythonProcess = null;
    if (code !== 0) setTimeout(startMediaCongoPythonScraper, 5000);
  });

  console.log(`✅ Scraper MEDIACONGO lancé (PID: ${mediacongoPythonProcess.pid})`);
}

function startPpdaPythonScraper() {
  if (ppdaPythonProcess && !ppdaPythonProcess.killed) {
    console.log(`✅ Scraper PPDA déjà en cours (PID: ${ppdaPythonProcess.pid})`);
    return;
  }

  const scriptPath = path.join(__dirname, 'scripts', 'PPDA.py');
  if (!fs.existsSync(scriptPath)) {
    console.error('❌ PPDA.py non trouvé !');
    return;
  }

  console.log('🚀 Démarrage du scraper PPDA...');
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  ppdaPythonProcess = spawn(pythonCmd, [scriptPath], {
    cwd: path.join(__dirname, 'scripts'),
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, PORT: '5017' }
  });

  ppdaPythonProcess.stdout.on('data', (data) => {
    console.log(`[PPDA STDOUT] ${data.toString().trim()}`);
  });

  ppdaPythonProcess.stderr.on('data', (data) => {
    console.error(`[PPDA STDERR] ${data.toString().trim()}`);
  });

  ppdaPythonProcess.on('close', (code) => {
    console.log(`❌ Scraper PPDA terminé avec code ${code}`);
    ppdaPythonProcess = null;
    if (code !== 0) setTimeout(startPpdaPythonScraper, 5000);
  });

  console.log(`✅ Scraper PPDA lancé (PID: ${ppdaPythonProcess.pid})`);
}

function startNigerPythonScraper() {
  if (nigerPythonProcess && !nigerPythonProcess.killed) {
    console.log(`✅ Scraper NIGER déjà en cours (PID: ${nigerPythonProcess.pid})`);
    return;
  }

  const scriptPath = path.join(__dirname, 'scripts', 'niger_api.py');
  if (!fs.existsSync(scriptPath)) {
    console.error('❌ niger_api.py non trouvé !');
    return;
  }

  console.log('🚀 Démarrage du scraper Niger Emploi...');
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  nigerPythonProcess = spawn(pythonCmd, [scriptPath], {
    cwd: path.join(__dirname, 'scripts'),
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, PORT: '5018' }
  });

  nigerPythonProcess.stdout.on('data', (data) => {
    console.log(`[NIGER STDOUT] ${data.toString().trim()}`);
  });

  nigerPythonProcess.stderr.on('data', (data) => {
    console.error(`[NIGER STDERR] ${data.toString().trim()}`);
  });

  nigerPythonProcess.on('close', (code) => {
    console.log(`❌ Scraper NIGER terminé avec code ${code}`);
    nigerPythonProcess = null;
    if (code !== 0) setTimeout(startNigerPythonScraper, 5000);
  });

  console.log(`✅ Scraper NIGER lancé (PID: ${nigerPythonProcess.pid})`);
}

function startSomaliaPythonScraper() {
  if (somaliaPythonProcess && !somaliaPythonProcess.killed) {
    console.log(`✅ Scraper SOMALIA déjà en cours (PID: ${somaliaPythonProcess.pid})`);
    return;
  }

  const scriptPath = path.join(__dirname, 'scripts', 'somalijobs_api.py');
  if (!fs.existsSync(scriptPath)) {
    console.error('❌ somalijobs_api.py non trouvé !');
    return;
  }

  console.log('🚀 Démarrage du scraper Somalia Jobs...');
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  somaliaPythonProcess = spawn(pythonCmd, [scriptPath], {
    cwd: path.join(__dirname, 'scripts'),
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, PORT: '5019' }
  });

  somaliaPythonProcess.stdout.on('data', (data) => {
    console.log(`[SOMALIA STDOUT] ${data.toString().trim()}`);
  });

  somaliaPythonProcess.stderr.on('data', (data) => {
    console.error(`[SOMALIA STDERR] ${data.toString().trim()}`);
  });

  somaliaPythonProcess.on('close', (code) => {
    console.log(`❌ Scraper SOMALIA terminé avec code ${code}`);
    somaliaPythonProcess = null;
    if (code !== 0) setTimeout(startSomaliaPythonScraper, 5000);
  });

  console.log(`✅ Scraper SOMALIA lancé (PID: ${somaliaPythonProcess.pid})`);
}

// ==================== HEALTH & INFO ====================
app.get('/health', async (req, res) => {
  const health = {
    node: 'healthy',
    timestamp: new Date().toISOString(),
    database: 'PostgreSQL - tenders_db',
    frontend: reactBuildExists ? 'build found' : 'build not found',
    services: {
      auth: 'available',
      users: 'available',
      tuneps: 'available',
      boamp: pythonProcess ? `running (PID: ${pythonProcess.pid})` : 'not started',
      pnud: pnudPythonProcess ? `running (PID: ${pnudPythonProcess.pid})` : 'not started',
      haicop: haicopPythonProcess ? `running (PID: ${haicopPythonProcess.pid})` : 'not started',
      banque: banquePythonProcess ? `running (PID: ${banquePythonProcess.pid})` : 'not started',
      tuneps_ao: tunepsAoPythonProcess ? `running (PID: ${tunepsAoPythonProcess.pid})` : 'not started'
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
        banque_scrape: 'POST /api/banque/api/scrape',
        tuneps_ao_scrape: 'POST /api/tuneps_ao/api/scrape'
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
          <h1>API Scraper avec Authentification</h1>
          <p><strong>Serveur Node.js</strong> sur port ${PORT}</p>
          
          <div class="endpoints">
            <h3>Authentification</h3>
            <ul>
              <li><code>POST /api/auth/register</code> - Inscription utilisateur</li>
              <li><code>POST /api/auth/login</code> - Connexion</li>
              <li><code>POST /api/users/create</code> - Créer utilisateur (ADMIN)</li>
            </ul>
          </div>
          
          <div>
            <h3>Tester avec Postman</h3>
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
  console.log(`Serveur Node.js démarré → http://localhost:${PORT}`);
  console.log('='.repeat(80) + '\n');

  // Démarrer tous les scrapers Python au démarrage
  startBoampPythonScraper();
  startPnudPythonScraper();  // ✅ ACTIVÉ - PostgreSQL Ready
  startBanquePythonScraper();  // ✅ ACTIVÉ - PostgreSQL Ready
  startHaicopPythonScraper();  // ✅ ACTIVÉ - PostgreSQL Ready (migrated)
  startTunepsAoPythonScraper();        // Maintenant correctement lancé
  startTunepsPythonScraper();
  startArmpPythonScraper();  // ✅ ACTIVÉ - PostgreSQL Ready
  startBeninPythonScraper();
  startExpertisePythonScraper();  // ✅ ACTIVÉ - PostgreSQL Ready
  startGizPythonScraper();
  startReliefPythonScraper();
  startMediaCongoPythonScraper();
  startPpdaPythonScraper();
  startNigerPythonScraper();
  startSomaliaPythonScraper();

  console.log(`
API AUTHENTIFICATION PRÊTE !

Endpoints:
• Register: POST http://localhost:${PORT}/api/auth/register
• Login: POST http://localhost:${PORT}/api/auth/login
• Créer user (ADMIN): POST http://localhost:${PORT}/api/users/create

Ports actifs:
• Backend Node.js: ${PORT}
• BOAMP: 5003
• TUNEPS: 5001
• TUNEPS AO: 5005
• PNUD: 5006
• ARMP: 5007
• BANQUE: 5010
• HAICOP: 5011
• BENIN: 5012
• EXPERTISE FRANCE: 5013
• GIZ: 5014
• RELIEF: 5015
• MEDIACONGO: 5016
• PPDA: 5017
• NIGER: 5018
  `);
});

// Gestion propre de l'arrêt
process.on('SIGINT', () => {
  console.log('\nArrêt du serveur demandé...');
  [
    pythonProcess, pnudPythonProcess, haicopPythonProcess, banquePythonProcess,
    tunepsAoPythonProcess, armpPythonProcess, beninPythonProcess,
    expertisePythonProcess, gizPythonProcess, tunepsPythonProcess, reliefPythonProcess,
    mediacongoPythonProcess, ppdaPythonProcess, nigerPythonProcess
  ].forEach(proc => {
    if (proc && !proc.killed) {
      console.log(`Arrêt PID: ${proc.pid}...`);
      proc.kill();
    }
  });
  process.exit(0);
});

module.exports = app;