// src/components/Navbar.js
import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import './Navbar.css';

const Navbar = () => {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <div className="navbar-brand">
          <Link to="/multi-sites">
            <span className="brand-icon">📊</span>
            <span className="brand-text">Extraction Automatique</span>
          </Link>
        </div>

        <button onClick={handleLogout} className="logout-button">
          <span className="logout-icon">🚪</span>
          <span className="logout-text">Déconnexion</span>
        </button>
      </div>
    </nav>
  );
};

export default Navbar;