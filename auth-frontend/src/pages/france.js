// src/pages/france.js
import React, { useState, useEffect } from 'react';

const France = () => {
  const [pending, setPending] = useState([]);
  const [tenders, setTenders] = useState([]);
  const [stats, setStats] = useState({});
  const [secteurs, setSecteurs] = useState([]);
  const [dateDebut, setDateDebut] = useState('2024-10-01');  // Fix: dates par défaut pour tests
  const [dateFin, setDateFin] = useState('2024-10-12');     // Fix: dates par défaut pour tests
  const [categories, setCategories] = useState(['informatique', 'textile', 'batiment']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchPending();
    fetchTenders();
    fetchStats();
    fetchSecteurs();
  }, []);

  const API_BASE = 'http://localhost:5004/api';

  const fetchWithErrorHandling = async (url, options = {}) => {
    try {
      const res = await fetch(url, options);
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      return await res.json();
    } catch (err) {
      console.error(`Erreur fetch ${url}:`, err);
      setError(err.message);
      throw err;
    }
  };

  const fetchPending = async () => {
    try {
      const data = await fetchWithErrorHandling(`${API_BASE}/pending`);
      setPending(data.pending || []);
    } catch (err) {
      console.error('Erreur fetch pending:', err);
    }
  };

  const fetchTenders = async () => {
    try {
      const data = await fetchWithErrorHandling(`${API_BASE}/tenders`);
      setTenders(data.tenders || []);
    } catch (err) {
      console.error('Erreur fetch tenders:', err);
    }
  };

  const fetchStats = async () => {
    try {
      const data = await fetchWithErrorHandling(`${API_BASE}/stats`);
      setStats(data.stats || {});
    } catch (err) {
      console.error('Erreur fetch stats:', err);
    }
  };

  const fetchSecteurs = async () => {
    try {
      const data = await fetchWithErrorHandling(`${API_BASE}/secteurs`);
      setSecteurs(data || []);
    } catch (err) {
      console.error('Erreur fetch secteurs:', err);
    }
  };

  const handleScrape = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/scrape`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date_debut: dateDebut || new Date().toISOString().split('T')[0],
          date_fin: dateFin || new Date().toISOString().split('T')[0],
          categories
        })
      });
      const data = await res.json();
      if (data.success) {
        alert(data.message);
        fetchPending();
      } else {
        alert('Erreur lors du scraping');
      }
    } catch (err) {
      console.error('Erreur scraping:', err);
      setError('Erreur lors du scraping: ' + err.message);
      alert('Erreur scraping: ' + err.message);
    }
    setLoading(false);
  };

  const handleValidate = async (reference) => {
    try {
      const res = await fetch(`${API_BASE}/validate/${reference}`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        alert('Offre validée !');
        fetchPending();
        fetchTenders();
        fetchStats();
      } else {
        alert(data.message || 'Erreur validation');
      }
    } catch (err) {
      console.error('Erreur validation:', err);
      alert('Erreur validation: ' + err.message);
    }
  };

  const handleDelete = async (reference) => {
    if (!window.confirm('Supprimer cette offre ?')) return;
    try {
      const res = await fetch(`${API_BASE}/delete_pending/${reference}`, { method: 'DELETE' });
      const data = await res.json();
      if (data.success) {
        alert('Offre supprimée !');
        fetchPending();
      } else {
        alert(data.message || 'Erreur suppression');
      }
    } catch (err) {
      console.error('Erreur suppression:', err);
      alert('Erreur suppression: ' + err.message);
    }
  };

  if (error) {
    return <div style={{ color: 'red' }}>Erreur: {error}</div>;
  }

  return (
    <div style={{ padding: '20px' }}>
      <h1>FranceJS - France Marchés Scraper</h1>
      
      {/* Stats */}
      <div style={{ marginBottom: '20px' }}>
        <h2>Statistiques</h2>
        <p>Total validées: {stats.total_validated || 0}</p>
        <p>Total en attente: {stats.total_pending || 0}</p>
        <ul>
          {Object.entries(stats.by_secteur || {}).map(([secteur, count]) => (
            <li key={secteur}>{secteur}: {count}</li>
          ))}
        </ul>
      </div>

      {/* Scraping Form */}
      <div style={{ marginBottom: '20px', border: '1px solid #ccc', padding: '10px' }}>
        <h2>Lancer un Scraping</h2>
        <input
          type="date"
          value={dateDebut}
          onChange={(e) => setDateDebut(e.target.value)}
        />
        <input
          type="date"
          value={dateFin}
          onChange={(e) => setDateFin(e.target.value)}
        />
        <select
          multiple
          value={categories}
          onChange={(e) => setCategories(Array.from(e.target.selectedOptions, option => option.value))}
          style={{ height: '100px' }}
        >
          <option value="informatique">Informatique</option>
          <option value="textile">Textile</option>
          <option value="batiment">Bâtiment</option>
        </select>
        <button onClick={handleScrape} disabled={loading}>
          {loading ? 'Scraping...' : 'Scraper'}
        </button>
      </div>

      {/* Pending Offres */}
      <div style={{ marginBottom: '20px' }}>
        <h2>Offres en Attente ({pending.length})</h2>
        <ul>
          {pending.map((offre) => (
            <li key={offre.reference} style={{ border: '1px solid #ccc', margin: '10px 0', padding: '10px' }}>
              <strong>{offre.reference}</strong> - {offre.description}
              <br />Secteur: {offre.secteur_activite} (ID: {offre.secteur_activite_id})
              <br />Date expiration: {offre.expirationDate}
              <button onClick={() => handleValidate(offre.reference)}>Valider</button>
              <button onClick={() => handleDelete(offre.reference)} style={{ marginLeft: '10px', color: 'red' }}>Supprimer</button>
              {offre.cahier_charge_pdf_filename && (
                <a href={`${API_BASE}/download_pdf/${offre.cahier_charge_pdf_filename}`} style={{ marginLeft: '10px' }} target="_blank" rel="noopener noreferrer">PDF</a>
              )}
            </li>
          ))}
        </ul>
      </div>

      {/* Validated Tenders */}
      <div>
        <h2>Tenders Validés ({tenders.length})</h2>
        <ul>
          {tenders.slice(0, 10).map((tender) => (
            <li key={tender._id} style={{ border: '1px solid #ccc', margin: '10px 0', padding: '10px' }}>
              <strong>{tender.reference}</strong> - {tender.description}
              <br />Secteur: {tender.secteur_activite}
              <br />Validation: {tender.validationDate}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default France;