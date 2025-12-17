require('dotenv').config();

module.exports = {
  port: process.env.PORT || 5000,
  mongoUri: process.env.MONGO_URI || 'mongodb://localhost:27017/appeloffres',
  jwtSecret: process.env.JWT_SECRET || 'super_secret_key',
  jwtExpiresIn: process.env.JWT_EXPIRES_IN || '7d'
};
