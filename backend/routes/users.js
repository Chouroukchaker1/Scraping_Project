const express = require('express');
const bcrypt = require('bcryptjs');
const User = require('../models/User');
const auth = require('../middleware/auth');

const router = express.Router();

// Créer un utilisateur (ADMIN/SUPER_ADMIN) - protégé
router.post('/create', auth(['SUPER_ADMIN','ADMIN']), async (req, res) => {
  const { name, email, password, role } = req.body;
  if (!name || !email || !password || !role) return res.status(400).json({ message: 'Tous les champs sont requis !' });

  const existing = await User.findOne({ email });
  if (existing) return res.status(400).json({ message: 'Utilisateur déjà existant !' });

  const hashedPassword = await bcrypt.hash(password, 10);
  const roleUpper = role.toUpperCase();
  if (!['SUPER_ADMIN','ADMIN','USER'].includes(roleUpper)) return res.status(400).json({ message: 'Role invalide !' });

  const newUser = new User({ name, email, password: hashedPassword, role: roleUpper });
  await newUser.save();

  res.status(201).json({ message: `${roleUpper} créé avec succès !`, user: { name, email, role: roleUpper } });
});

module.exports = router;
