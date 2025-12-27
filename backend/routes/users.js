// routes/users.js
const express = require('express');
const bcrypt = require('bcryptjs');
const User = require('../models/User');
const auth = require('../middleware/auth');

const router = express.Router();

// CRÉER UN UTILISATEUR - Protégé (ADMIN/SUPER_ADMIN)
router.post('/create', auth(['ADMIN', 'SUPER_ADMIN']), async (req, res) => {
  try {
    const { name, email, password, role } = req.body;
    
    // Validation
    if (!name || !email || !password || !role) {
      return res.status(400).json({ 
        success: false,
        message: 'Tous les champs sont requis' 
      });
    }

    // Vérifier les rôles valides
    const validRoles = ['USER', 'ADMIN', 'SUPER_ADMIN'];
    const roleUpper = role.toUpperCase();
    
    if (!validRoles.includes(roleUpper)) {
      return res.status(400).json({ 
        success: false,
        message: 'Rôle invalide. Rôles acceptés: USER, ADMIN, SUPER_ADMIN' 
      });
    }

    // Vérifier si l'utilisateur existe déjà
    const existingUser = await User.findOne({ email });
    if (existingUser) {
      return res.status(400).json({ 
        success: false,
        message: 'Un utilisateur avec cet email existe déjà' 
      });
    }

    // Hasher le mot de passe
    const hashedPassword = await bcrypt.hash(password, 10);

    // Créer l'utilisateur
    const user = new User({
      name,
      email,
      password: hashedPassword,
      role: roleUpper
    });

    await user.save();

    res.status(201).json({
      success: true,
      message: `Utilisateur ${roleUpper} créé avec succès`,
      user: {
        id: user._id,
        name: user.name,
        email: user.email,
        role: user.role
      }
    });
  } catch (error) {
    console.error('Create user error:', error);
    res.status(500).json({ 
      success: false,
      message: 'Erreur serveur',
      error: error.message 
    });
  }
});

// GET PROFILE - Protégé (tous utilisateurs authentifiés)
router.get('/profile', auth(), async (req, res) => {
  try {
    const user = await User.findById(req.user.id).select('-password');
    
    if (!user) {
      return res.status(404).json({ 
        success: false,
        message: 'Utilisateur non trouvé' 
      });
    }

    res.json({
      success: true,
      user
    });
  } catch (error) {
    console.error('Profile error:', error);
    res.status(500).json({ 
      success: false,
      message: 'Erreur serveur',
      error: error.message 
    });
  }
});

// GET ALL USERS - Protégé (ADMIN/SUPER_ADMIN)
router.get('/all', auth(['ADMIN', 'SUPER_ADMIN']), async (req, res) => {
  try {
    const users = await User.find().select('-password').sort({ createdAt: -1 });
    
    res.json({
      success: true,
      count: users.length,
      users
    });
  } catch (error) {
    console.error('Get users error:', error);
    res.status(500).json({ 
      success: false,
      message: 'Erreur serveur',
      error: error.message 
    });
  }
});

module.exports = router;