const jwt = require('jsonwebtoken');
const { jwtSecret } = require('../config');

function auth(requiredRoles = []) {
  if (typeof requiredRoles === 'string') requiredRoles = [requiredRoles];

  return (req, res, next) => {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer '))
      return res.status(401).json({ message: 'Missing token' });

    const token = authHeader.split(' ')[1];
    try {
      const payload = jwt.verify(token, jwtSecret);
      req.user = payload;

      if (requiredRoles.length && !requiredRoles.includes(payload.role)) {
        return res.status(403).json({ message: 'Forbidden - role' });
      }

      next();
    } catch (err) {
      return res.status(401).json({ message: 'Invalid token' });
    }
  };
}

module.exports = auth;
