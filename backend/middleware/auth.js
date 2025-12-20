// middleware/auth.js
const jwt = require('jsonwebtoken');

const auth = (roles = []) => {
  return (req, res, next) => {
    const token = req.header('Authorization')?.replace('Bearer ', '');

    if (!token) {
      return res.status(401).json({ message: 'Accès non autorisé. Token manquant.' });
    }

    try {
      const decoded = jwt.verify(token, process.env.JWT_SECRET || 'votre_secret_jwt');
      req.user = decoded;

      // Vérifier les rôles si spécifiés
      if (roles.length > 0 && !roles.includes(decoded.role)) {
        return res.status(403).json({ message: 'Accès interdit. Rôle insuffisant.' });
      }

      next();
    } catch (error) {
      return res.status(401).json({ message: 'Token invalide.' });
    }
  };
};

module.exports = auth;