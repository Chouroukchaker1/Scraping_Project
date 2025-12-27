// 1️⃣ Charger dotenv
require('dotenv').config();

const mongoose = require('mongoose');
const User = require('./models/User'); // chemin vers ton modèle User

// 2️⃣ Récupérer l'URI depuis process.env
const MONGO_URI = process.env.MONGO_URI;

if (!MONGO_URI) {
  console.error("❌ MONGO_URI est undefined. Vérifie ton fichier .env !");
  process.exit(1);
}

// 3️⃣ Connexion à MongoDB
mongoose.connect(MONGO_URI)
  .then(async () => {
    console.log('✅ Connecté à MongoDB !');
    const users = await User.find();
    console.log('👥 Utilisateurs existants :', users);
    mongoose.connection.close();
  })
  .catch(err => console.error('Erreur MongoDB:', err));
