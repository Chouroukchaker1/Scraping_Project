// src/pages/Tuneps.js - VERSION PROFESSIONNELLE COMPLÈTE
import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { Search, Calendar, CheckCircle, Edit2, Trash2, RefreshCw, Play, AlertCircle } from 'lucide-react';
import './Tuneps.css';

const API_BASE = 'http://localhost:5000/api/tuneps';

const arabicStyle = {
  fontFamily: '"Noto Sans Arabic", "Arial Unicode MS", Tahoma, Arial, sans-serif',
  direction: 'auto',
  textAlign: 'right',
  whiteSpace: 'pre-wrap',
  unicodeBidi: 'plaintext'
};

// ===== FORMULAIRE DE SCRAPING =====
const ScrapeForm = ({ onScrape, loading, error }) => {
  const [dates, setDates] = useState({ 
    start: new Date().toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0] 
  });
  const [extractionComplete, setExtractionComplete] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (new Date(dates.start) > new Date(dates.end)) {
      alert("La date de début ne peut pas être postérieure à la date de fin.");
      return;
    }
    onScrape({ ...dates, extraction_complete: extractionComplete });
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
          <Search size={24} color="#0066CC" />
          Rechercher des Appels d'Offres
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
        
        <label style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          padding: '1rem',
          background: '#F8FAFC',
          borderRadius: '10px',
          cursor: 'pointer',
          marginBottom: '1.5rem',
          border: '2px solid #E2E8F0'
        }}>
          <input
            type="checkbox"
            checked={extractionComplete}
            onChange={(e) => setExtractionComplete(e.target.checked)}
            style={{
              width: '20px',
              height: '20px',
              cursor: 'pointer'
            }}
          />
          <span style={{ fontSize: '0.95rem', color: '#475569', fontWeight: '500' }}>
            Mode extraction complète (plus lent mais plus détaillé)
          </span>
        </label>
        
        <button
          type="submit"
          disabled={loading}
          style={{
            width: '100%',
            padding: '1rem',
            background: loading ? '#94A3B8' : 'linear-gradient(135deg, #0066CC 0%, #00A0DC 100%)',
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
const PendingList = ({ offres, onValidate, onUpdate, onDelete, processing }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState('');
  const [itemsPerPage, setItemsPerPage] = useState(50);

  const filteredOffres = useMemo(() => 
    offres.filter(o => 
      o.reference?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (o.description && o.description.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (o.promoter && o.promoter.toLowerCase().includes(searchTerm.toLowerCase()))
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

  const handleValidate = async (reference) => {
    if (!window.confirm(`Valider l'offre ${reference} ?`)) return;
    try {
      const response = await axios.post(`${API_BASE}/validate/${encodeURIComponent(reference)}`);
      if (!response.data.success) throw new Error(response.data.message);
      onValidate(reference);
      alert(`✅ Offre ${reference} validée avec succès`);
    } catch (err) {
      handleError(err, "Erreur lors de la validation");
    }
  };

  const handleUpdate = async (offre) => {
    const newRegionId = prompt('Nouveau ID Région:', offre.region_id || '');
    if (newRegionId !== null && newRegionId.trim() !== '') {
      try {
        const response = await axios.post(`${API_BASE}/update/${encodeURIComponent(offre.reference)}`, {
          region_id: parseInt(newRegionId, 10),
        });
        if (!response.data.success) throw new Error(response.data.message);
        onUpdate(offre.reference, { region_id: parseInt(newRegionId, 10) });
        alert(`✅ Offre ${offre.reference} mise à jour`);
      } catch (err) {
        handleError(err, "Erreur lors de la mise à jour");
      }
    }
  };

  const handleDelete = async (reference) => {
    if (!window.confirm(`Supprimer définitivement l'offre ${reference} ?`)) return;
    try {
      const response = await axios.delete(`${API_BASE}/delete/${encodeURIComponent(reference)}`);
      if (!response.data.success) throw new Error(response.data.message);
      onDelete(reference);
      alert(`✅ Offre ${reference} supprimée avec succès`);
    } catch (err) {
      handleError(err, "Erreur lors de la suppression");
    }
  };

  const handleDeleteAll = async () => {
    if (!window.confirm(`ATTENTION: Supprimer TOUTES les ${filteredOffres.length} offres en attente ?\n\nCette action est irréversible!`)) return;
    try {
      const response = await axios.delete(`${API_BASE}/delete-all`);
      if (!response.data.success) throw new Error(response.data.message);
      alert(`✅ ${response.data.deletedCount} offres supprimées avec succès`);
      window.location.reload();
    } catch (err) {
      handleError(err, "Erreur lors de la suppression globale");
    }
  };

  const handleError = (err, defaultMessage) => {
    let message = defaultMessage;
    if (err.response) {
      message = err.response.data?.message || `${defaultMessage} (HTTP ${err.response.status})`;
    } else if (err.request) {
      message = "Pas de réponse du serveur. Vérifiez que le backend est lancé.";
    } else {
      message = err.message;
    }
    setError(message);
    setTimeout(() => setError(''), 8000);
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
          background: 'linear-gradient(135deg, #0066CC 0%, #00A0DC 100%)',
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
              placeholder="Rechercher par référence, description ou promoteur..."
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
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Acheteur</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Publiée</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Limite</th>
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
                    <td style={{ ...arabicStyle, padding: '1rem', verticalAlign: 'top', maxWidth: '300px' }}>
                      <span style={{ color: '#475569' }}>
                        {offre.description?.substring(0, 120)}{offre.description?.length > 120 ? '...' : ''}
                      </span>
                    </td>
                    <td style={{ ...arabicStyle, padding: '1rem', verticalAlign: 'top', color: '#475569' }}>
                      {offre.promoter}
                    </td>
                    <td style={{ padding: '1rem', verticalAlign: 'top', color: '#475569' }}>{formatDate(offre.publicationDate)}</td>
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
                          onClick={() => handleUpdate(offre)}
                          style={{
                            padding: '0.5rem 0.75rem',
                            background: 'linear-gradient(135deg, #0D9488 0%, #0F766E 100%)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.25rem'
                          }}
                          title="Modifier"
                        >
                          <Edit2 size={16} />
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
                  background: currentPage === 1 ? '#F1F5F9' : '#0066CC',
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
                  background: currentPage === 1 ? '#F1F5F9' : '#0066CC',
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
                  background: currentPage === totalPages ? '#F1F5F9' : '#0066CC',
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
                  background: currentPage === totalPages ? '#F1F5F9' : '#0066CC',
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

// ===== LISTE DES OFFRES VALIDÉES =====
const ValidatedList = ({ tenders, loading, error, currentPage, setCurrentPage, onDelete }) => {
  const [localError, setLocalError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [itemsPerPage, setItemsPerPage] = useState(50);

  const filteredTenders = useMemo(() => 
    tenders.filter(t => 
      t.reference?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (t.description && t.description.toLowerCase().includes(searchTerm.toLowerCase()))
    ),
    [tenders, searchTerm]
  );

  const totalPages = Math.max(1, Math.ceil(filteredTenders.length / itemsPerPage));

  useEffect(() => {
    if (currentPage > totalPages && totalPages > 0) {
      setCurrentPage(totalPages);
    }
  }, [filteredTenders, totalPages, currentPage, setCurrentPage]);

  const formatDate = (dateStr) => {
    if (!dateStr || dateStr === 'N/A') return 'N/A';
    try {
      const date = new Date(dateStr);
      return date.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
    } catch {
      return dateStr;
    }
  };

  const handleDelete = async (reference) => {
    if (!window.confirm(`Supprimer définitivement l'offre validée ${reference} ?`)) return;
    try {
      const response = await axios.delete(`${API_BASE}/validated/delete/${encodeURIComponent(reference)}`);
      if (!response.data.success) throw new Error(response.data.message);
      onDelete(reference);
      alert(`✅ Offre validée ${reference} supprimée avec succès`);
    } catch (err) {
      handleError(err, "Erreur lors de la suppression");
    }
  };

  const handleError = (err, defaultMessage) => {
    let message = defaultMessage;
    if (err.response) {
      message = err.response.data?.message || `${defaultMessage} (HTTP ${err.response.status})`;
    } else if (err.request) {
      message = "Pas de réponse du serveur. Vérifiez que le backend est lancé.";
    } else {
      message = err.message;
    }
    setLocalError(message);
    setTimeout(() => setLocalError(''), 8000);
  };

  const paginatedTenders = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredTenders.slice(start, start + itemsPerPage);
  }, [filteredTenders, currentPage, itemsPerPage]);

  if (loading) return (
    <div style={{
      background: 'white',
      borderRadius: '16px',
      padding: '3rem',
      boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
      textAlign: 'center',
      color: '#64748B'
    }}>
      <RefreshCw size={32} className="spinning" style={{ marginBottom: '1rem' }} />
      <p>Chargement des offres validées...</p>
    </div>
  );

  return (
    <div style={{
      background: 'white',
      borderRadius: '16px',
      padding: '2rem',
      boxShadow: '0 4px 12px rgba(0,0,0,0.05)'
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
        ✅ Offres Validées
        <span style={{
          background: 'linear-gradient(135deg, #059669 0%, #047857 100%)',
          color: 'white',
          padding: '0.25rem 0.75rem',
          borderRadius: '20px',
          fontSize: '0.9rem',
          fontWeight: '600'
        }}>
          {filteredTenders.length}
        </span>
      </h2>
      
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '1.5rem',
        flexWrap: 'wrap',
        gap: '1rem'
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
              placeholder="Rechercher par référence ou description..."
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
      {localError && (
        <div style={{
          padding: '1rem',
          background: '#FEE2E2',
          border: '1px solid #FCA5A5',
          borderRadius: '8px',
          color: '#991B1B',
          marginBottom: '1rem'
        }}>
          {localError}
        </div>
      )}
      
      {filteredTenders.length === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '3rem',
          color: '#64748B'
        }}>
          <p style={{ fontSize: '1.1rem' }}>📭 Aucune offre validée</p>
          <p style={{ fontSize: '0.9rem', marginTop: '0.5rem' }}>
            Validez d'abord des offres depuis la liste "Offres en Attente"
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
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Acheteur</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Publiée</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Limite</th>
                  <th style={{ padding: '1rem', textAlign: 'center', fontWeight: '600', color: '#475569' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {paginatedTenders.map((tender, idx) => (
                  <tr key={tender.reference || idx} style={{
                    borderBottom: '1px solid #E2E8F0',
                    transition: 'background 0.2s'
                  }}>
                    <td style={{ padding: '1rem', verticalAlign: 'top' }}>
                      <strong style={{ color: '#0F172A' }}>{tender.reference}</strong>
                      {tender.validationDate && (
                        <div style={{ fontSize: '0.75rem', color: '#059669', marginTop: '0.25rem' }}>
                          ✅ Validée le: {new Date(tender.validationDate).toLocaleDateString('fr-FR')}
                        </div>
                      )}
                    </td>
                    <td style={{ ...arabicStyle, padding: '1rem', verticalAlign: 'top', maxWidth: '300px' }}>
                      <span style={{ color: '#475569' }}>
                        {tender.description?.substring(0, 120)}{tender.description?.length > 120 ? '...' : ''}
                      </span>
                    </td>
                    <td style={{ ...arabicStyle, padding: '1rem', verticalAlign: 'top', color: '#475569' }}>{tender.promoter}</td>
                    <td style={{ padding: '1rem', verticalAlign: 'top', color: '#475569' }}>{formatDate(tender.publicationDate)}</td>
                    <td style={{ padding: '1rem', verticalAlign: 'top', color: '#475569' }}>{formatDate(tender.expirationDate)}</td>
                    <td style={{ padding: '1rem', textAlign: 'center', verticalAlign: 'top' }}>
                      <button 
                        onClick={() => handleDelete(tender.reference)} 
                        style={{ 
                          padding: '0.5rem 0.75rem',
                          background: 'linear-gradient(135deg, #DC2626 0%, #B91C1C 100%)',
                          color: 'white',
                          border: 'none',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.25rem',
                          margin: '0 auto'
                        }}
                        title="Supprimer"
                      >
                        <Trash2 size={16} />
                      </button>
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
                  background: currentPage === 1 ? '#F1F5F9' : '#059669',
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
                  background: currentPage === 1 ? '#F1F5F9' : '#059669',
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
                  background: currentPage === totalPages ? '#F1F5F9' : '#059669',
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
                  background: currentPage === totalPages ? '#F1F5F9' : '#059669',
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
const Tuneps = () => {
  const [pendingOffres, setPendingOffres] = useState([]);
  const [validatedTenders, setValidatedTenders] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [loadingScrape, setLoadingScrape] = useState(false);
  const [loadingValidated, setLoadingValidated] = useState(false);
  const [error, setError] = useState('');
  const [validatedPage, setValidatedPage] = useState(1);

  const fetchPendingOffres = async () => {
    try {
      const response = await axios.get(`${API_BASE}/pending?page=1&limit=100`);
      if (response.data.success) {
        const offers = response.data.data?.offers || [];
        setPendingOffres(offers);
        setProcessing(response.data.scraping?.isProcessing || false);
      }
    } catch (err) {
      console.error('Error fetching pending:', err.message);
      setPendingOffres([]);
    }
  };

  const fetchValidatedTenders = async () => {
    setLoadingValidated(true);
    try {
      const response = await axios.get(`${API_BASE}/validated`);
      if (response.data.success) {
        setValidatedTenders(response.data.tenders || []);
      }
    } catch (err) {
      console.error('Error fetching validated:', err.message);
      setValidatedTenders([]);
    } finally {
      setLoadingValidated(false);
    }
  };

  const handleScrape = async (params) => {
    setLoadingScrape(true);
    setError('');
    try {
      const response = await axios.post(`${API_BASE}/scrape`, {
        start_date: params.start,
        end_date: params.end,
        extraction_complete: params.extraction_complete || false
      });
      
      if (response.data.success) {
        alert('✅ Scraping démarré avec succès! Rafraîchissez dans 30-60 secondes.');
        setProcessing(true);
        
        const interval = setInterval(() => {
          fetchPendingOffres();
        }, 5000);
        
        setTimeout(() => {
          clearInterval(interval);
          setProcessing(false);
        }, 120000);
      }
    } catch (err) {
      setError(err.response?.data?.message || err.message || 'Erreur de connexion');
    } finally {
      setLoadingScrape(false);
    }
  };

  const handleValidate = (ref) => {
    setPendingOffres(prev => prev.filter(o => o.reference !== ref));
    fetchValidatedTenders();
  };

  const handleUpdate = (ref, data) => {
    setPendingOffres(prev =>
      prev.map(o => (o.reference === ref ? { ...o, ...data } : o))
    );
  };

  const handleDelete = (ref) => {
    setPendingOffres(prev => prev.filter(o => o.reference !== ref));
  };

  const handleDeleteValidated = (ref) => {
    setValidatedTenders(prev => prev.filter(t => t.reference !== ref));
  };

  useEffect(() => {
    fetchPendingOffres();
    fetchValidatedTenders();
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
            background: 'linear-gradient(135deg, #0066CC 0%, #00A0DC 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            marginBottom: '0.5rem'
          }}>
            🇹🇳 Scraper TUNEPS
          </h1>
          <p style={{ color: '#64748B', fontSize: '1.1rem' }}>
            Extraction automatique des appels d'offres
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
            <span style={{ color: '#0066CC', fontWeight: '700', marginLeft: '0.5rem' }}>
              {pendingOffres.length} en attente
            </span>
            <span style={{ color: '#94A3B8', margin: '0 0.5rem' }}>•</span>
            <span style={{ color: '#059669', fontWeight: '700' }}>
              {validatedTenders.length} validées
            </span>
          </div>
          
          <button
            onClick={() => { fetchPendingOffres(); fetchValidatedTenders(); }}
            style={{
              padding: '0.75rem 1.5rem',
              background: 'linear-gradient(135deg, #0066CC 0%, #00A0DC 100%)',
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

        <ScrapeForm 
          onScrape={handleScrape} 
          loading={loadingScrape} 
          error={error} 
        />

        <PendingList
          offres={pendingOffres}
          onValidate={handleValidate}
          onUpdate={handleUpdate}
          onDelete={handleDelete}
          processing={processing}
        />

        <ValidatedList
          tenders={validatedTenders}
          loading={loadingValidated}
          error={error}
          currentPage={validatedPage}
          setCurrentPage={setValidatedPage}
          onDelete={handleDeleteValidated}
        />
      </div>
    </div>
  );
};

export default Tuneps;