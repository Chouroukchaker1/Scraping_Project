const { PythonShell } = require('python-shell');
const Offre = require('../models/Offre');
const path = require('path');

exports.scrapeOffres = async (req, res) => {
  const { date_debut, date_fin, categories } = req.body;

  const options = {
    mode: 'json',
    pythonPath: 'python3', // Adjust for Windows if needed
    scriptPath: path.join(__dirname, '../scripts'),
    args: [JSON.stringify({ date_debut, date_fin, categories })],
  };

  try {
    const results = await new Promise((resolve, reject) => {
      PythonShell.run('scraper.py', options, (err, results) => {
        if (err) return reject(err);
        resolve(results);
      });
    });

    const offres = results[0]?.offres || [];

    // Save to MongoDB
    for (const offre of offres) {
      try {
        const existingOffre = await Offre.findOne({ reference: offre.reference });
        if (!existingOffre) {
          await Offre.create(offre);
        } else {
          await Offre.updateOne({ reference: offre.reference }, { $set: offre });
        }
      } catch (err) {
        console.error(`Error saving offre ${offre.reference}:`, err);
      }
    }

    res.json({ success: true, message: 'Scraping completed', offres });
  } catch (error) {
    console.error('Scraping error:', error);
    res.status(500).json({ success: false, message: 'Scraping error', error: error.message });
  }
};

exports.getOffres = async (req, res) => {
  try {
    const offres = await Offre.find().sort({ createdAt: -1 });
    res.json({ success: true, offres });
  } catch (error) {
    res.status(500).json({ success: false, message: 'Error fetching offres', error: error.message });
  }
};

exports.getSecteurs = async (req, res) => {
  const options = {
    mode: 'json',
    pythonPath: 'python3',
    scriptPath: path.join(__dirname, '../scripts'),
    args: ['--get-secteurs'],
  };

  try {
    const results = await new Promise((resolve, reject) => {
      PythonShell.run('scraper.py', options, (err, results) => {
        if (err) return reject(err);
        resolve(results);
      });
    });

    res.json({ success: true, secteurs: results[0] });
  } catch (error) {
    res.status(500).json({ success: false, message: 'Error fetching secteurs', error: error.message });
  }
};

exports.validateOffre = async (req, res) => {
  const { reference } = req.params;
  const options = {
    mode: 'json',
    pythonPath: 'python3',
    scriptPath: path.join(__dirname, '../scripts'),
    args: ['--validate', reference],
  };

  try {
    const result = await new Promise((resolve, reject) => {
      PythonShell.run('scraper.py', options, (err, results) => {
        if (err) return reject(err);
        resolve(results[0]);
      });
    });

    if (result.success) {
      await Offre.deleteOne({ reference });
    }

    res.json(result);
  } catch (error) {
    res.status(500).json({ success: false, message: 'Error validating offre', error: error.message });
  }
};

exports.updateOffre = async (req, res) => {
  const { reference } = req.params;
  const updatedData = req.body;

  const options = {
    mode: 'json',
    pythonPath: 'python3',
    scriptPath: path.join(__dirname, '../scripts'),
    args: ['--update', reference, JSON.stringify(updatedData)],
  };

  try {
    const result = await new Promise((resolve, reject) => {
      PythonShell.run('scraper.py', options, (err, results) => {
        if (err) return reject(err);
        resolve(results[0]);
      });
    });

    if (result.success) {
      await Offre.updateOne({ reference }, { $set: updatedData });
    }

    res.json(result);
  } catch (error) {
    res.status(500).json({ success: false, message: 'Error updating offre', error: error.message });
  }
};

exports.downloadPdf = async (req, res) => {
  const { filename } = req.params;
  const filePath = path.join(__dirname, '../scripts/cahiers-charges-pdf', filename);

  res.download(filePath, filename, (err) => {
    if (err) {
      res.status(404).json({ success: false, message: 'PDF not found' });
    }
  });
};

module.exports = { scrapeOffres, getOffres, getSecteurs, validateOffre, updateOffre, downloadPdf };