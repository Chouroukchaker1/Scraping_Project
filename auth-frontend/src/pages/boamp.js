// src/pages/Boamp.js - VERSION PROFESSIONNELLE COMPLÈTE
import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { Search, Calendar, CheckCircle, Trash2, RefreshCw, Play, AlertCircle, Key } from 'lucide-react';
import './Boamp.css';

const API_BASE = '/api/boamp';

// ===== FORMULAIRE DE SCRAPING =====
const ScrapeForm = ({ onScrape, loading, error, keywords }) => {
  const [dates, setDates] = useState({ 
    start: '',
    end: '' 
  });
  const [showKeywords, setShowKeywords] = useState(false);

  useEffect(() => {
    const today = new Date().toISOString().split('T')[0];
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    setDates({
      start: weekAgo.toISOString().split('T')[0],
      end: today
    });
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (new Date(dates.start) > new Date(dates.end)) {
      alert("La date de début ne peut pas être postérieure à la date de fin.");
      return;
    }
    onScrape(dates);
  };

  return (
    <div style={{
      background: 'white',
      borderRadius: '16px',
      padding: '2rem',
      boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
      marginBottom: '2rem'
    }}>
      <form onSubmit={handleSubmit}>
        <h2 style={{
          fontSize: '1.5rem',
          fontWeight: '700',
          color: '#0F172A',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem'
        }}>
          <Search size={24} color="#9b59b6" />
          Rechercher des Marchés Publics
        </h2>
        
        {error && (
          <div style={{
            background: '#FEE2E2',
            border: '1px solid #FCA5A5',
            borderRadius: '8px',
            padding: '1rem',
            marginBottom: '1rem',
            color: '#991B1B',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <AlertCircle size={20} />
            {error}
          </div>
        )}
        
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
          gap: '1.5rem',
          marginBottom: '1.5rem'
        }}>
          <div>
            <label style={{
              display: 'block',
              fontSize: '0.9rem',
              fontWeight: '600',
              color: '#475569',
              marginBottom: '0.5rem'
            }}>
              <Calendar size={16} style={{ display: 'inline', marginRight: '0.5rem', verticalAlign: 'middle' }} />
              Date Début
            </label>
            <input
              type="date"
              value={dates.start}
              onChange={(e) => setDates({ ...dates, start: e.target.value })}
              required
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '2px solid #E2E8F0',
                borderRadius: '10px',
                fontSize: '0.95rem',
                transition: 'all 0.2s'
              }}
            />
          </div>
          
          <div>
            <label style={{
              display: 'block',
              fontSize: '0.9rem',
              fontWeight: '600',
              color: '#475569',
              marginBottom: '0.5rem'
            }}>
              <Calendar size={16} style={{ display: 'inline', marginRight: '0.5rem', verticalAlign: 'middle' }} />
              Date Fin
            </label>
            <input
              type="date"
              value={dates.end}
              onChange={(e) => setDates({ ...dates, end: e.target.value })}
              required
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '2px solid #E2E8F0',
                borderRadius: '10px',
                fontSize: '0.95rem',
                transition: 'all 0.2s'
              }}
            />
          </div>
        </div>
        
        <div style={{
          background: '#F8FAFC',
          borderRadius: '10px',
          padding: '1rem',
          marginBottom: '1.5rem',
          border: '2px solid #E2E8F0'
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: showKeywords ? '1rem' : '0'
          }}>
            <span style={{ fontSize: '0.95rem', color: '#475569', fontWeight: '500' }}>
              <Key size={16} style={{ display: 'inline', marginRight: '0.5rem', verticalAlign: 'middle' }} />
              {keywords.length} mots-clés configurés
            </span>
            <button
              type="button"
              onClick={() => setShowKeywords(!showKeywords)}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#9b59b6',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '0.9rem'
              }}
            >
              {showKeywords ? 'Masquer' : 'Afficher'}
            </button>
          </div>
          
          {showKeywords && (
            <div style={{ 
              display: 'flex', 
              flexWrap: 'wrap', 
              gap: '0.5rem',
              marginTop: '1rem'
            }}>
              {keywords.map((kw, i) => (
                <span key={i} style={{
                  padding: '0.25rem 0.75rem',
                  background: 'linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%)',
                  color: 'white',
                  borderRadius: '15px',
                  fontSize: '0.85rem',
                  fontWeight: '500'
                }}>
                  {kw}
                </span>
              ))}
            </div>
          )}
        </div>
        
        <button
          type="submit"
          disabled={loading}
          style={{
            width: '100%',
            padding: '1rem',
            background: loading ? '#94A3B8' : 'linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%)',
            color: 'white',
            border: 'none',
            borderRadius: '10px',
            fontSize: '1rem',
            fontWeight: '600',
            cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.75rem',
            transition: 'all 0.2s'
          }}
        >
          {loading ? (
            <>
              <RefreshCw size={20} className="spinning" />
              Scraping en cours...
            </>
          ) : (
            <>
              <Play size={20} />
              Lancer le Scraping
            </>
          )}
        </button>
      </form>
    </div>
  );
};

// ===== LISTE DES OFFRES EN ATTENTE =====
const PendingList = ({ offres, onValidate, onDelete, processing, onDeleteAll }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState('');
  const [itemsPerPage, setItemsPerPage] = useState(50);

  const filteredOffres = useMemo(() => 
    offres.filter(o => 
      o.reference?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (o.description && o.description.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (o.secteur_activite && o.secteur_activite.toLowerCase().includes(searchTerm.toLowerCase()))
    ),
    [offres, searchTerm]
  );

  const totalPages = Math.max(1, Math.ceil(filteredOffres.length / itemsPerPage));

  useEffect(() => {
    if (currentPage > totalPages && totalPages > 0) {
      setCurrentPage(totalPages);
    }
  }, [filteredOffres, totalPages, currentPage]);

  const formatDate = (dateStr) => {
    if (!dateStr || dateStr === 'N/A') return 'N/A';
    try {
      const date = new Date(dateStr);
      return date.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
    } catch {
      return dateStr;
    }
  };

  const handleValidate = (reference) => {
    if (!window.confirm(`Valider l'offre ${reference} ?`)) return;
    onValidate(reference);
  };

  const handleDelete = (reference) => {
    if (!window.confirm(`Supprimer l'offre ${reference} ?`)) return;
    onDelete(reference);
  };

  const handleDeleteAll = () => {
    if (!window.confirm(`ATTENTION: Supprimer TOUTES les ${filteredOffres.length} offres en attente ?\n\nCette action est irréversible!`)) return;
    onDeleteAll();
  };

  const paginatedOffres = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredOffres.slice(start, start + itemsPerPage);
  }, [filteredOffres, currentPage, itemsPerPage]);

  return (
    <div style={{
      background: 'white',
      borderRadius: '16px',
      padding: '2rem',
      boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
      marginBottom: '2rem'
    }}>
      <h2 style={{
        fontSize: '1.5rem',
        fontWeight: '700',
        color: '#0F172A',
        marginBottom: '1.5rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem'
      }}>
        ⏳ Offres en Attente
        <span style={{
          background: 'linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%)',
          color: 'white',
          padding: '0.25rem 0.75rem',
          borderRadius: '20px',
          fontSize: '0.9rem',
          fontWeight: '600'
        }}>
          {filteredOffres.length}
        </span>
      </h2>
      
      {processing && (
        <div style={{
          padding: '1rem',
          background: '#FEF3C7',
          border: '1px solid #FDE047',
          borderRadius: '8px',
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          color: '#854D0E'
        }}>
          <RefreshCw size={20} className="spinning" />
          Scraping en cours... Rafraîchissez dans quelques secondes.
        </div>
      )}
      
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1.5rem',
        gap: '1rem',
        flexWrap: 'wrap'
      }}>
        <div style={{ flex: '1', minWidth: '300px' }}>
          <div style={{ position: 'relative' }}>
            <Search size={20} style={{
              position: 'absolute',
              left: '1rem',
              top: '50%',
              transform: 'translateY(-50%)',
              color: '#94A3B8'
            }} />
            <input
              type="text"
              placeholder="Rechercher par référence, description ou secteur..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                width: '100%',
                padding: '0.75rem 1rem 0.75rem 3rem',
                border: '2px solid #E2E8F0',
                borderRadius: '10px',
                fontSize: '0.95rem'
              }}
            />
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <select
            value={itemsPerPage}
            onChange={(e) => {
              setItemsPerPage(parseInt(e.target.value));
              setCurrentPage(1);
            }}
            style={{
              padding: '0.75rem',
              border: '2px solid #E2E8F0',
              borderRadius: '10px',
              fontSize: '0.9rem',
              fontWeight: '500'
            }}
          >
            <option value="10">10 / page</option>
            <option value="25">25 / page</option>
            <option value="50">50 / page</option>
            <option value="100">100 / page</option>
            <option value="200">200 / page</option>
          </select>

          {filteredOffres.length > 0 && (
            <button
              onClick={handleDeleteAll}
              style={{
                padding: '0.75rem 1.25rem',
                background: 'linear-gradient(135deg, #DC2626 0%, #B91C1C 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '10px',
                fontWeight: '600',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}
            >
              <Trash2 size={18} />
              Tout Supprimer
            </button>
          )}
        </div>
      </div>
      
      {error && (
        <div style={{
          padding: '1rem',
          background: '#FEE2E2',
          border: '1px solid #FCA5A5',
          borderRadius: '8px',
          color: '#991B1B',
          marginBottom: '1rem'
        }}>
          {error}
        </div>
      )}
      
      {filteredOffres.length === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '3rem',
          color: '#64748B'
        }}>
          <p style={{ fontSize: '1.1rem' }}>📭 Aucune offre en attente</p>
          <p style={{ fontSize: '0.9rem', marginTop: '0.5rem' }}>
            Lancez un scraping pour commencer !
          </p>
        </div>
      ) : (
        <>
          <div style={{
            overflowX: 'auto',
            borderRadius: '10px',
            border: '1px solid #E2E8F0'
          }}>
            <table style={{
              width: '100%',
              borderCollapse: 'collapse'
            }}>
              <thead>
                <tr style={{
                  background: '#F8FAFC',
                  borderBottom: '2px solid #E2E8F0'
                }}>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Référence</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Description</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Secteur</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Mots-clés</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Date Limite</th>
                  <th style={{ padding: '1rem', textAlign: 'center', fontWeight: '600', color: '#475569' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {paginatedOffres.map((offre, idx) => (
                  <tr key={offre.reference || idx} style={{
                    borderBottom: '1px solid #E2E8F0',
                    transition: 'background 0.2s'
                  }}>
                    <td style={{ padding: '1rem', verticalAlign: 'top' }}>
                      <strong style={{ color: '#0F172A' }}>{offre.reference}</strong>
                    </td>
                    <td style={{ padding: '1rem', verticalAlign: 'top', maxWidth: '300px' }}>
                      {offre.url_source ? (
                        <a 
                          href={offre.url_source} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          style={{ 
                            color: '#9b59b6', 
                            textDecoration: 'none',
                            fontWeight: '500'
                          }}
                        >
                          {offre.description?.substring(0, 120)}{offre.description?.length > 120 ? '...' : ''}
                        </a>
                      ) : (
                        <span style={{ color: '#475569' }}>
                          {offre.description?.substring(0, 120)}{offre.description?.length > 120 ? '...' : ''}
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '1rem', verticalAlign: 'top', color: '#475569' }}>
                      {offre.secteur_activite || 'N/A'}
                    </td>
                    <td style={{ padding: '1rem', verticalAlign: 'top' }}>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                        {offre.mots_cles_detectes?.slice(0, 2).map((kw, i) => (
                          <span key={i} style={{
                            padding: '0.15rem 0.5rem',
                            background: '#F3E8FF',
                            color: '#7C3AED',
                            borderRadius: '10px',
                            fontSize: '0.75rem',
                            fontWeight: '500'
                          }}>
                            {kw}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td style={{ padding: '1rem', verticalAlign: 'top', color: '#475569' }}>{formatDate(offre.expirationDate)}</td>
                    <td style={{ padding: '1rem', textAlign: 'center', verticalAlign: 'top' }}>
                      <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                        <button
                          onClick={() => handleValidate(offre.reference)}
                          style={{
                            padding: '0.5rem 0.75rem',
                            background: 'linear-gradient(135deg, #059669 0%, #047857 100%)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.25rem'
                          }}
                          title="Valider"
                        >
                          <CheckCircle size={16} />
                        </button>
                        <button
                          onClick={() => handleDelete(offre.reference)}
                          style={{
                            padding: '0.5rem 0.75rem',
                            background: 'linear-gradient(135deg, #DC2626 0%, #B91C1C 100%)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.25rem'
                          }}
                          title="Supprimer"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div style={{
              marginTop: '2rem',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: '0.5rem',
              flexWrap: 'wrap'
            }}>
              <button
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
                style={{
                  padding: '0.5rem 1rem',
                  background: currentPage === 1 ? '#F1F5F9' : '#9b59b6',
                  color: currentPage === 1 ? '#94A3B8' : 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                  fontWeight: '600'
                }}
              >
                ⏮️
              </button>
              
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                style={{
                  padding: '0.5rem 1rem',
                  background: currentPage === 1 ? '#F1F5F9' : '#9b59b6',
                  color: currentPage === 1 ? '#94A3B8' : 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                  fontWeight: '600'
                }}
              >
                ⬅️
              </button>

              <span style={{
                padding: '0.5rem 1rem',
                background: '#F8FAFC',
                borderRadius: '8px',
                fontWeight: '600',
                color: '#475569'
              }}>
                Page {currentPage} / {totalPages}
              </span>

              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                style={{
                  padding: '0.5rem 1rem',
                  background: currentPage === totalPages ? '#F1F5F9' : '#9b59b6',
                  color: currentPage === totalPages ? '#94A3B8' : 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                  fontWeight: '600'
                }}
              >
                ➡️
              </button>
              
              <button
                onClick={() => setCurrentPage(totalPages)}
                disabled={currentPage === totalPages}
                style={{
                  padding: '0.5rem 1rem',
                  background: currentPage === totalPages ? '#F1F5F9' : '#9b59b6',
                  color: currentPage === totalPages ? '#94A3B8' : 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                  fontWeight: '600'
                }}
              >
                ⏭️
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

// ===== COMPOSANT PRINCIPAL =====
const BoampDashboard = () => {
  const [keywords, setKeywords] = useState([]);
  const [stats, setStats] = useState(null);
  const [pendingOffres, setPendingOffres] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [loadingScrape, setLoadingScrape] = useState(false);
  const [error, setError] = useState('');

  const fetchAllData = async () => {
    try {
      const [keywordsRes, statsRes, pendingRes] = await Promise.all([
        axios.get(`${API_BASE}/keywords`).catch(() => ({ data: { success: false } })),
        axios.get(`${API_BASE}/stats`).catch(() => ({ data: { success: false } })),
        axios.get(`${API_BASE}/pending?page=1&limit=1000`).catch(() => ({ data: { success: false } }))
      ]);

      if (keywordsRes.data.success) setKeywords(keywordsRes.data.keywords || []);
      if (statsRes.data.success) setStats(statsRes.data.stats);
      if (pendingRes.data.success && pendingRes.data.pending) {
        setPendingOffres(pendingRes.data.pending.offres || []);
      }

      if (!keywordsRes.data.success || !statsRes.data.success || !pendingRes.data.success) {
        setError("⚠️ Serveur Python (BOAMP) non démarré ou inaccessible (port 5003)");
      } else {
        setError('');
      }
    } catch (err) {
      setError("❌ Erreur de connexion au serveur BOAMP");
      console.error(err);
    }
  };

  const handleScrape = async (dates) => {
    setLoadingScrape(true);
    setError('');
    try {
      const response = await axios.post(`${API_BASE}/scrape`, {
        date_debut: dates.start,
        date_fin: dates.end
      });
      
      if (response.data.success) {
        const newCount = response.data.stats?.new || 0;
        alert(`✅ Scraping terminé avec succès!\n${newCount} nouvelles offres trouvées.`);
        setProcessing(true);
        
        const interval = setInterval(() => {
          fetchAllData();
        }, 5000);
        
        setTimeout(() => {
          clearInterval(interval);
          setProcessing(false);
        }, 60000);
      }
    } catch (err) {
      setError(err.response?.data?.message || err.message || 'Erreur de connexion');
    } finally {
      setLoadingScrape(false);
    }
  };

  const handleValidate = async (reference) => {
    try {
      const response = await axios.post(`${API_BASE}/validate/${encodeURIComponent(reference)}`);
      if (response.data.success) {
        alert(`✅ Offre ${reference} validée et envoyée à l'API !`);
        setPendingOffres(prev => prev.filter(o => o.reference !== reference));
        fetchAllData();
      } else {
        alert(`❌ Erreur: ${response.data.message}`);
      }
    } catch (err) {
      alert('❌ Erreur lors de la validation');
      console.error(err);
    }
  };

  const handleDelete = async (reference) => {
    try {
      await axios.delete(`${API_BASE}/delete/${encodeURIComponent(reference)}`);
      alert(`🗑️ Offre ${reference} supprimée avec succès`);
      setPendingOffres(prev => prev.filter(o => o.reference !== reference));
      fetchAllData();
    } catch (err) {
      alert('❌ Erreur lors de la suppression');
      console.error(err);
    }
  };

  const handleDeleteAll = async () => {
    try {
      const response = await axios.post(`${API_BASE}/clean-pending`);
      alert(`🧹 ${response.data.count || 0} offres supprimées avec succès`);
      fetchAllData();
    } catch (err) {
      alert('❌ Erreur lors du nettoyage');
      console.error(err);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(to bottom, #F8FAFC 0%, #F1F5F9 100%)',
      padding: '2rem'
    }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        <div style={{
          textAlign: 'center',
          marginBottom: '2rem'
        }}>
          <h1 style={{
            fontSize: '2.5rem',
            fontWeight: '800',
            background: 'linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            marginBottom: '0.5rem'
          }}>
            🇫🇷 Scraper BOAMP
          </h1>
          <p style={{ color: '#64748B', fontSize: '1.1rem' }}>
            Extraction automatique des marchés publics français
          </p>
        </div>

        <div style={{
          background: 'white',
          borderRadius: '12px',
          padding: '1.5rem',
          marginBottom: '2rem',
          boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem'
        }}>
          <div>
            <span style={{ fontWeight: '600', color: '#475569' }}>
              📊 Statistiques: 
            </span>
            <span style={{ color: '#9b59b6', fontWeight: '700', marginLeft: '0.5rem' }}>
              {stats?.total_pending || 0} en attente
            </span>
            <span style={{ color: '#94A3B8', margin: '0 0.5rem' }}>•</span>
            <span style={{ color: '#059669', fontWeight: '700' }}>
              {stats?.total_validated || 0} validées
            </span>
            <span style={{ color: '#94A3B8', margin: '0 0.5rem' }}>•</span>
            <span style={{ color: '#f39c12', fontWeight: '700' }}>
              {keywords.length} mots-clés
            </span>
          </div>
          
          <button
            onClick={() => { fetchAllData(); }}
            style={{
              padding: '0.75rem 1.5rem',
              background: 'linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '10px',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}
          >
            <RefreshCw size={18} />
            Rafraîchir
          </button>
        </div>

        {error && (
          <div style={{
            background: '#FEE2E2',
            border: '1px solid #FCA5A5',
            borderRadius: '12px',
            padding: '1rem',
            marginBottom: '2rem',
            color: '#991B1B',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <AlertCircle size={20} />
            {error}
          </div>
        )}

        <ScrapeForm 
          onScrape={handleScrape} 
          loading={loadingScrape} 
          error={error}
          keywords={keywords}
        />

        <PendingList
          offres={pendingOffres}
          onValidate={handleValidate}
          onDelete={handleDelete}
          processing={processing}
          onDeleteAll={handleDeleteAll}
        />
      </div>
    </div>
  );
};

export default BoampDashboard;