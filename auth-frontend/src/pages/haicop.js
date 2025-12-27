// src/pages/Haicop.js - VERSION PROFESSIONNELLE COMPLÈTE
import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { Search, Calendar, CheckCircle, Edit2, Trash2, RefreshCw, Play, AlertCircle, Globe, Send, Building, ExternalLink, Filter } from 'lucide-react';
import './Haicop.css';

const API_BASE = 'http://localhost:5011/api';

// ===== FORMULAIRE DE SCRAPING =====
const ScrapeForm = ({ onScrape, loading, error, onCleanDuplicates }) => {
  const [formData, setFormData] = useState({
    date_filtre: '',
    max_pages: 4
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onScrape(formData);
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
          <Building size={24} color="#27ae60" />
          Scraping des Marchés Publics Tunisiens HAICOP
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
              Date Filtre (DD-MM-YYYY)
            </label>
            <input
              type="text"
              value={formData.date_filtre}
              onChange={(e) => setFormData({ ...formData, date_filtre: e.target.value })}
              placeholder="Ex: 01-12-2024 ou ALL"
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
              <Filter size={16} style={{ display: 'inline', marginRight: '0.5rem', verticalAlign: 'middle' }} />
              Nombre Max de Pages
            </label>
            <input
              type="number"
              value={formData.max_pages}
              onChange={(e) => setFormData({ ...formData, max_pages: parseInt(e.target.value) || 10 })}
              min="1"
              max="100"
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
          ℹ️ Format date: DD-MM-YYYY (ex: 15-12-2024). Laisser vide ou mettre "ALL" pour toutes les dates.
          <br />
          ⚠️ Le scraping est lourd, utilisez un nombre limité de pages.
        </div>
        
        <div style={{
          display: 'flex',
          gap: '1rem',
          flexWrap: 'wrap'
        }}>
          <button
            type="submit"
            disabled={loading}
            style={{
              flex: '1',
              minWidth: '200px',
              padding: '1rem',
              background: loading ? '#94A3B8' : 'linear-gradient(135deg, #27ae60 0%, #219653 100%)',
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
                Lancer le Scraping HAICOP
              </>
            )}
          </button>
          
          <button
            type="button"
            onClick={() => {
              if (window.confirm('Nettoyer les doublons dans la collection pending ?')) {
                onCleanDuplicates();
              }
            }}
            style={{
              padding: '1rem 1.5rem',
              background: 'linear-gradient(135deg, #e67e22 0%, #d35400 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '10px',
              fontSize: '1rem',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              transition: 'all 0.2s'
            }}
          >
            <Trash2 size={20} />
            Nettoyer Doublons
          </button>
        </div>
      </form>
    </div>
  );
};

// ===== LISTE DES OFFRES EN ATTENTE =====
const PendingList = ({ offres, onValidate, onDelete, processing, onPostAll }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [itemsPerPage, setItemsPerPage] = useState(50);

  const filteredOffres = useMemo(() => 
    offres.filter(o => 
      o.reference?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (o.description?.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (o.promoter?.toLowerCase().includes(searchTerm.toLowerCase()))
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
      return date.toLocaleString('fr-FR', { 
        dateStyle: 'short', 
        timeStyle: 'short' 
      });
    } catch {
      return dateStr;
    }
  };

  const handleValidate = (reference) => {
    if (!window.confirm(`Valider et poster l'offre ${reference} ?`)) return;
    onValidate(reference);
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
        ⏳ Offres en Attente HAICOP
        <span style={{
          background: 'linear-gradient(135deg, #27ae60 0%, #219653 100%)',
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
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Description</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Promoteur</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Date Publication</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Date Expiration</th>
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
                      <span style={{ color: '#475569' }}>
                        {(offre.description || '').substring(0, 120)}
                        {(offre.description || '').length > 120 ? '...' : ''}
                      </span>
                    </td>
                    <td style={{ padding: '1rem', verticalAlign: 'top', color: '#475569' }}>
                      {offre.promoter || 'N/A'}
                    </td>
                    <td style={{ padding: '1rem', verticalAlign: 'top', color: '#475569', whiteSpace: 'nowrap' }}>
                      {formatDate(offre.publicationDate)}
                    </td>
                    <td style={{ padding: '1rem', verticalAlign: 'top', color: '#475569', whiteSpace: 'nowrap' }}>
                      <span style={{ 
                        color: offre.expirationDate && new Date(offre.expirationDate) < new Date() ? '#DC2626' : '#059669',
                        fontWeight: '500'
                      }}>
                        {formatDate(offre.expirationDate)}
                      </span>
                    </td>
                    <td style={{ padding: '1rem', textAlign: 'center', verticalAlign: 'top' }}>
                      <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center', flexWrap: 'wrap' }}>
                        <button
                          onClick={() => handleValidate(offre.reference)}
                          style={{
                            padding: '0.5rem 0.75rem',
                            background: 'linear-gradient(135deg, #27ae60 0%, #219653 100%)',
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
                  background: currentPage === 1 ? '#F1F5F9' : '#27ae60',
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
                  background: currentPage === 1 ? '#F1F5F9' : '#27ae60',
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
                  background: currentPage === totalPages ? '#F1F5F9' : '#27ae60',
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
                  background: currentPage === totalPages ? '#F1F5F9' : '#27ae60',
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
      (t.promoter?.toLowerCase().includes(searchTerm.toLowerCase()))
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
      return date.toLocaleString('fr-FR', { 
        dateStyle: 'short', 
        timeStyle: 'short' 
      });
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
        ✅ Offres Validées HAICOP
        <span style={{
          background: 'linear-gradient(135deg, #27ae60 0%, #219653 100%)',
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
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Description</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Promoteur</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Date Publication</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600', color: '#475569' }}>Date Validation</th>
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
                      <span style={{ color: '#475569' }}>
                        {(tender.description || '').substring(0, 120)}
                        {(tender.description || '').length > 120 ? '...' : ''}
                      </span>
                    </td>
                    <td style={{ padding: '1rem', verticalAlign: 'top', color: '#475569' }}>
                      {tender.promoter || 'N/A'}
                    </td>
                    <td style={{ padding: '1rem', verticalAlign: 'top', color: '#475569', whiteSpace: 'nowrap' }}>
                      {formatDate(tender.publicationDate)}
                    </td>
                    <td style={{ padding: '1rem', verticalAlign: 'top', color: '#475569', whiteSpace: 'nowrap' }}>
                      {formatDate(tender.validationDate)}
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
                  background: currentPage === 1 ? '#F1F5F9' : '#27ae60',
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
                  background: currentPage === 1 ? '#F1F5F9' : '#27ae60',
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
                  background: currentPage === totalPages ? '#F1F5F9' : '#27ae60',
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
                  background: currentPage === totalPages ? '#F1F5F9' : '#27ae60',
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
const Haicop = () => {
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
        setError('⚠️ Service HAICOP non disponible');
      } else {
        setError('');
      }
    } catch (err) {
      setHealth({ error: err.message });
      setError('❌ Erreur de connexion au serveur HAICOP');
    }
  };

  const fetchPendingOffres = async () => {
    try {
      const response = await axios.get(`${API_BASE}/pending-all`);
      if (response.data.success) {
        setPendingOffres(response.data.offres || []);
      }
    } catch (err) {
      console.error('Error fetching pending:', err.message);
      setPendingOffres([]);
    }
  };

  const fetchValidatedTenders = async () => {
    setLoadingValidated(true);
    try {
      const response = await axios.get(`${API_BASE}/validated-all`);
      if (response.data.success) {
        setValidatedTenders(response.data.offres || []);
      }
    } catch (err) {
      console.error('Error fetching validated:', err.message);
      setValidatedTenders([]);
    } finally {
      setLoadingValidated(false);
    }
  };

  const handleScrape = async (formData) => {
    setLoadingScrape(true);
    setError('');
    try {
      const response = await axios.post(`${API_BASE}/scrape-tunisie`, formData);
      
      if (response.data.success) {
        alert('✅ Scraping HAICOP démarré avec succès! Rafraîchissez dans quelques minutes.');
        setProcessing(true);
        
        const interval = setInterval(() => {
          fetchPendingOffres();
        }, 10000);
        
        setTimeout(() => {
          clearInterval(interval);
          setProcessing(false);
        }, 180000); // 3 minutes pour HAICOP
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

  const handleCleanDuplicates = async () => {
    try {
      const response = await axios.post(`${API_BASE}/clean-duplicates`);
      if (response.data.success) {
        alert(response.data.message);
        fetchPendingOffres();
      } else {
        alert(`❌ Erreur: ${response.data.message}`);
      }
    } catch (err) {
      alert('❌ Erreur lors du nettoyage des doublons');
      console.error(err);
    }
  };

  const handlePostAll = async () => {
    try {
      const response = await axios.post(`${API_BASE}/post-pending-all`);
      const { posted, failed, remaining } = response.data;
      alert(`✅ Résultats:\n${posted} offres postées\n${failed} échecs\n${remaining} restantes`);
      fetchPendingOffres();
      fetchValidatedTenders();
    } catch (err) {
      alert('❌ Erreur lors du post global');
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
            background: 'linear-gradient(135deg, #27ae60 0%, #219653 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            marginBottom: '0.5rem'
          }}>
            🇹🇳 Scraper HAICOP Tunisie
          </h1>
          <p style={{ color: '#64748B', fontSize: '1.1rem' }}>
            Extraction automatique des marchés publics tunisiens (HAICOP)
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
                  background: '#27ae60',
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
            <span style={{ color: '#27ae60', fontWeight: '700', marginLeft: '0.5rem' }}>
              {pendingOffres.length} en attente
            </span>
            <span style={{ color: '#94A3B8', margin: '0 0.5rem' }}>•</span>
            <span style={{ color: '#059669', fontWeight: '700' }}>
              {validatedTenders.length} validées
            </span>
          </div>
          
          <button
            onClick={() => { fetchPendingOffres(); fetchValidatedTenders(); fetchHealth(); }}
            style={{
              padding: '0.75rem 1.5rem',
              background: 'linear-gradient(135deg, #27ae60 0%, #219653 100%)',
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
          onCleanDuplicates={handleCleanDuplicates}
        />

        <PendingList
          offres={pendingOffres}
          onValidate={handleValidate}
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

export default Haicop;