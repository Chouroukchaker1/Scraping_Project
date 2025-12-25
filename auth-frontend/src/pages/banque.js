// src/pages/Banque.js - VERSION PROFESSIONNELLE COMPLÈTE
import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { Search, Calendar, CheckCircle, Edit2, Trash2, RefreshCw, Play, AlertCircle, Globe, Send, Banknote, ExternalLink, FileText } from 'lucide-react';
import './Banque.css';

const API_BASE = '/api/banque/api';

// ===== FORMULAIRE DE SCRAPING =====
const ScrapeForm = ({ onScrape, loading, error }) => {
  const [dates, setDates] = useState({ 
    start: '',
    end: '' 
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (dates.start && dates.end && new Date(dates.start) > new Date(dates.end)) {
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
          <Banknote size={24} color="#1E3A8A" />
          Rechercher des Marchés Publics Banque Mondiale
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
              Date Début (obligatoire)
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
              Date Fin (obligatoire)
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
          background: '#F0F8FF',
          borderRadius: '10px',
          padding: '1rem',
          marginBottom: '1.5rem',
          border: '2px solid #DBEAFE',
          fontSize: '0.9rem',
          color: '#1E40AF'
        }}>
          ℹ️ Le scraping de la Banque Mondiale nécessite obligatoirement une période définie (max 7 jours recommandé)
        </div>
        
        <button
          type="submit"
          disabled={loading}
          style={{
            width: '100%',
            padding: '1rem',
            background: loading ? '#94A3B8' : 'linear-gradient(135deg, #1E3A8A 0%, #0F2B64 100%)',
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
              Lancer le Scraping Banque Mondiale
            </>
          )}
        </button>
      </form>
    </div>
  );
};

// ===== LISTE DES OFFRES EN ATTENTE =====
const PendingList = ({ offres, onValidate, onUpdate, onDelete, processing, onPostAll }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [itemsPerPage, setItemsPerPage] = useState(50);

  const filteredOffres = useMemo(() => 
    offres.filter(o => 
      o.reference?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (o.description?.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (o.title?.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (o.pays?.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (o.country?.toLowerCase().includes(searchTerm.toLowerCase()))
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
    if (!window.confirm(`Valider et poster l'offre ${reference} ?`)) return;
    onValidate(reference);
  };

  const handleUpdate = (offre) => {
    const newCountryId = prompt('Nouveau ID Pays:', offre.country_id || '');
    if (newCountryId !== null && newCountryId.trim() !== '') {
      const id = parseInt(newCountryId, 10);
      if (!isNaN(id)) {
        onUpdate(offre.reference, id);
      } else {
        alert('ID pays invalide');
      }
    }
  };

  const handleDelete = (reference) => {
    if (!window.confirm(`Supprimer l'offre ${reference} ?`)) return;
    onDelete(reference);
  };

  const handlePostAll = () => {
    if (!window.confirm(`Poster TOUTES les ${filteredOffres.length} offres en attente ?\n\nElles seront envoyées à l'API.`)) return;
    onPostAll();
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
        ⏳ Offres en Attente Banque Mondiale
        <span style={{
          background: 'linear-gradient(135deg, #1E3A8A 0%, #0F2B64 100%)',
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
              placeholder="Rechercher par référence, description ou pays..."
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
              onClick={handlePostAll}
              style={{
                padding: '0.75rem 1.25rem',
                background: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
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
              <Send size={18} />
              Poster Toutes
            </button>
          )}
        </div>
      </div>
      
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
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Titre / Description</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Pays</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Date Publication</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Promoteur</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Liens</th>
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
                      <div style={{ marginBottom: '0.25rem', fontWeight: '600', color: '#1E293B' }}>
                        {offre.title || 'Sans titre'}
                      </div>
                      <span style={{ color: '#475569', fontSize: '0.9rem' }}>
                        {(offre.description || '').substring(0, 120)}
                        {(offre.description || '').length > 120 ? '...' : ''}
                      </span>
                    </td>
                    <td style={{ padding: '1rem', verticalAlign: 'top' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Globe size={16} color="#1E3A8A" />
                        <span style={{ color: '#475569' }}>
                          {offre.pays || offre.country || 'N/A'}
                        </span>
                      </div>
                      {offre.country_id && (
                        <span style={{ 
                          fontSize: '0.75rem', 
                          color: '#94A3B8',
                          display: 'block',
                          marginTop: '0.25rem'
                        }}>
                          ID: {offre.country_id}
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '1rem', verticalAlign: 'top', color: '#475569' }}>{formatDate(offre.publicationDate)}</td>
                    <td style={{ padding: '1rem', verticalAlign: 'top', color: '#475569' }}>{offre.promoter || 'Banque Mondiale'}</td>
                    <td style={{ padding: '1rem', verticalAlign: 'top' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                        {offre.url_source && (
                          <a 
                            href={offre.url_source} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            style={{ 
                              color: '#1E3A8A', 
                              textDecoration: 'none',
                              fontSize: '0.85rem',
                              fontWeight: '500',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.25rem'
                            }}
                          >
                            <ExternalLink size={14} />
                            Source
                          </a>
                        )}
                        {offre.document_url && (
                          <a 
                            href={offre.document_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            style={{ 
                              color: '#DC2626', 
                              textDecoration: 'none',
                              fontSize: '0.85rem',
                              fontWeight: '500',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.25rem'
                            }}
                          >
                            <FileText size={14} />
                            Document
                          </a>
                        )}
                      </div>
                    </td>
                    <td style={{ padding: '1rem', textAlign: 'center', verticalAlign: 'top' }}>
                      <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center', flexWrap: 'wrap' }}>
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
                            gap: '0.25rem',
                            fontSize: '0.85rem'
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
                            gap: '0.25rem',
                            fontSize: '0.85rem'
                          }}
                          title="Modifier Pays"
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
                            gap: '0.25rem',
                            fontSize: '0.85rem'
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
                  background: currentPage === 1 ? '#F1F5F9' : '#1E3A8A',
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
                  background: currentPage === 1 ? '#F1F5F9' : '#1E3A8A',
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
                  background: currentPage === totalPages ? '#F1F5F9' : '#1E3A8A',
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
                  background: currentPage === totalPages ? '#F1F5F9' : '#1E3A8A',
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
const ValidatedList = ({ tenders, loading }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [itemsPerPage, setItemsPerPage] = useState(50);

  const filteredTenders = useMemo(() => 
    tenders.filter(t => 
      t.reference?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (t.description?.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (t.title?.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (t.pays?.toLowerCase().includes(searchTerm.toLowerCase()))
    ),
    [tenders, searchTerm]
  );

  const totalPages = Math.max(1, Math.ceil(filteredTenders.length / itemsPerPage));

  useEffect(() => {
    if (currentPage > totalPages && totalPages > 0) {
      setCurrentPage(totalPages);
    }
  }, [filteredTenders, totalPages, currentPage]);

  const formatDate = (dateStr) => {
    if (!dateStr || dateStr === 'N/A') return 'N/A';
    try {
      const date = new Date(dateStr);
      return date.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
    } catch {
      return dateStr;
    }
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
        ✅ Offres Validées Banque Mondiale
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
              placeholder="Rechercher par référence, titre ou pays..."
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
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Titre / Description</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Pays</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Date Publication</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Date Validation</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Liens</th>
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
                    </td>
                    <td style={{ padding: '1rem', verticalAlign: 'top', maxWidth: '300px' }}>
                      <div style={{ marginBottom: '0.25rem', fontWeight: '600', color: '#1E293B' }}>
                        {tender.title || 'Sans titre'}
                      </div>
                      <span style={{ color: '#475569', fontSize: '0.9rem' }}>
                        {(tender.description || '').substring(0, 120)}
                        {(tender.description || '').length > 120 ? '...' : ''}
                      </span>
                    </td>
                    <td style={{ padding: '1rem', verticalAlign: 'top' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Globe size={16} color="#059669" />
                        <span style={{ color: '#475569' }}>
                          {tender.pays || tender.country || 'N/A'}
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: '1rem', verticalAlign: 'top', color: '#475569' }}>{formatDate(tender.publicationDate)}</td>
                    <td style={{ padding: '1rem', verticalAlign: 'top', color: '#475569' }}>{formatDate(tender.validationDate)}</td>
                    <td style={{ padding: '1rem', verticalAlign: 'top' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                        {tender.url_source && (
                          <a 
                            href={tender.url_source} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            style={{ 
                              color: '#1E3A8A', 
                              textDecoration: 'none',
                              fontSize: '0.85rem',
                              fontWeight: '500'
                            }}
                          >
                            🔗 Source
                          </a>
                        )}
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
const Banque = () => {
  const [pendingOffres, setPendingOffres] = useState([]);
  const [validatedTenders, setValidatedTenders] = useState([]);
  const [health, setHealth] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [loadingScrape, setLoadingScrape] = useState(false);
  const [loadingValidated, setLoadingValidated] = useState(false);
  const [error, setError] = useState('');

  const fetchHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE}/health`);
      setHealth(response.data);
      if (response.data.error) {
        setError('⚠️ Service Banque Mondiale non disponible');
      } else {
        setError('');
      }
    } catch (err) {
      setHealth({ error: err.message });
      setError('❌ Erreur de connexion au serveur Banque Mondiale');
    }
  };

  const fetchPendingOffres = async () => {
    try {
      const response = await axios.get(`${API_BASE}/pending`);
      if (response.data.success) {
        setPendingOffres(response.data.pending || []);
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
        setValidatedTenders(response.data.validated || []);
      }
    } catch (err) {
      console.error('Error fetching validated:', err.message);
      setValidatedTenders([]);
    } finally {
      setLoadingValidated(false);
    }
  };

  const handleScrape = async (dates) => {
    setLoadingScrape(true);
    setError('');
    try {
      const response = await axios.post(`${API_BASE}/scrape`, {
        startDate: dates.start,
        endDate: dates.end
      });
      
      if (response.data.success) {
        alert('✅ Scraping Banque Mondiale démarré avec succès! Rafraîchissez dans quelques minutes.');
        setProcessing(true);
        
        const interval = setInterval(() => {
          fetchPendingOffres();
        }, 10000);
        
        setTimeout(() => {
          clearInterval(interval);
          setProcessing(false);
        }, 120000);
      } else {
        setError(response.data.message || 'Erreur lors du scraping');
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
        alert(`✅ Offre ${reference} validée et postée avec succès !`);
        setPendingOffres(prev => prev.filter(o => o.reference !== reference));
        fetchValidatedTenders();
      } else {
        alert(`❌ Erreur: ${response.data.message}`);
      }
    } catch (err) {
      alert('❌ Erreur lors de la validation');
      console.error(err);
    }
  };

  const handleUpdate = async (reference, countryId) => {
    try {
      await axios.post(`${API_BASE}/update/${encodeURIComponent(reference)}`, {
        country_id: countryId
      });
      alert(`✅ Pays mis à jour pour l'offre ${reference}`);
      fetchPendingOffres();
    } catch (err) {
      alert('❌ Erreur lors de la mise à jour');
      console.error(err);
    }
  };

  const handleDelete = async (reference) => {
    try {
      const response = await axios.delete(`${API_BASE}/delete/${encodeURIComponent(reference)}`);
      if (response.data.success) {
        alert(`🗑️ Offre ${reference} supprimée avec succès`);
        setPendingOffres(prev => prev.filter(o => o.reference !== reference));
      } else {
        alert(`❌ Erreur: ${response.data.message}`);
      }
    } catch (err) {
      alert('❌ Erreur lors de la suppression');
      console.error(err);
    }
  };

  const handlePostAll = async () => {
    try {
      const response = await axios.post(`${API_BASE}/post_pending`);
      const { posted, failed, remaining } = response.data;
      alert(`✅ Résultats:\n${posted} offres postées\n${failed} échecs\n${remaining} restantes`);
      fetchPendingOffres();
      fetchValidatedTenders();
    } catch (err) {
      alert('❌ Erreur lors du post global');
      console.error(err);
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm(`⚠️ ATTENTION ⚠️\n\nVoulez-vous vraiment SUPPRIMER TOUTES les ${pendingOffres.length} offres en attente ?\n\nCette action est IRRÉVERSIBLE !`)) {
      return;
    }

    try {
      const response = await axios.delete(`${API_BASE}/clear_pending`);
      if (response.data.success) {
        alert(`✅ ${response.data.deleted_count} offres supprimées avec succès !`);
        setPendingOffres([]);
        fetchHealth();
      } else {
        alert(`❌ Erreur: ${response.data.message}`);
      }
    } catch (err) {
      alert('❌ Erreur lors de la suppression globale');
      console.error(err);
    }
  };

  useEffect(() => {
    fetchHealth();
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
            background: 'linear-gradient(135deg, #1E3A8A 0%, #0F2B64 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            marginBottom: '0.5rem'
          }}>
            🏦 Scraper Banque Mondiale
          </h1>
          <p style={{ color: '#64748B', fontSize: '1.1rem' }}>
            Extraction automatique des marchés publics africains de la Banque Mondiale
          </p>
        </div>

        {/* Health Status */}
        {health && (
          <div style={{
            background: health.error ? '#FEE2E2' : '#DCFCE7',
            borderRadius: '12px',
            padding: '1.5rem',
            marginBottom: '2rem',
            border: `2px solid ${health.error ? '#FCA5A5' : '#86EFAC'}`
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '1rem'
            }}>
              <div>
                <h3 style={{ 
                  margin: '0 0 0.5rem 0', 
                  color: health.error ? '#991B1B' : '#166534',
                  fontSize: '1.1rem',
                  fontWeight: '600'
                }}>
                  {health.error ? '⚠️ Service Indisponible' : '✅ Service Opérationnel'}
                </h3>
                {!health.error && (
                  <div style={{ fontSize: '0.9rem', color: '#475569' }}>
                    <span style={{ fontWeight: '600' }}>Status:</span> {health.status || 'OK'} | 
                    <span style={{ fontWeight: '600', marginLeft: '0.5rem' }}>DB:</span> {health.db_connected ? '✓ Connectée' : '✗ Déconnectée'}
                  </div>
                )}
              </div>
              <button
                onClick={fetchHealth}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#1E3A8A',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  fontSize: '0.9rem'
                }}
              >
                <RefreshCw size={16} style={{ display: 'inline', marginRight: '0.5rem', verticalAlign: 'middle' }} />
                Vérifier
              </button>
            </div>
          </div>
        )}

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
            <span style={{ color: '#1E3A8A', fontWeight: '700', marginLeft: '0.5rem' }}>
              {pendingOffres.length} en attente
            </span>
            <span style={{ color: '#94A3B8', margin: '0 0.5rem' }}>•</span>
            <span style={{ color: '#059669', fontWeight: '700' }}>
              {validatedTenders.length} validées
            </span>
          </div>

          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            {pendingOffres.length > 0 && (
              <button
                onClick={handleClearAll}
                style={{
                  padding: '0.75rem 1.5rem',
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
                Supprimer Tout
              </button>
            )}

            <button
              onClick={() => { fetchPendingOffres(); fetchValidatedTenders(); fetchHealth(); }}
              style={{
                padding: '0.75rem 1.5rem',
                background: 'linear-gradient(135deg, #1E3A8A 0%, #0F2B64 100%)',
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
        />

        <PendingList
          offres={pendingOffres}
          onValidate={handleValidate}
          onUpdate={handleUpdate}
          onDelete={handleDelete}
          processing={processing}
          onPostAll={handlePostAll}
        />

        <ValidatedList
          tenders={validatedTenders}
          loading={loadingValidated}
        />
      </div>
    </div>
  );
};

export default Banque;