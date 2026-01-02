// src/pages/MediaCongo.js - VERSION PROFESSIONNELLE COMPLÈTE
import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { Search, Calendar, CheckCircle, Edit2, Trash2, RefreshCw, Play, AlertCircle, Globe, Send, Newspaper, ExternalLink, FileText } from 'lucide-react';
import './MediaCongo.css';

const API_BASE = '/api/mediacongo/api';

// ===== FORMULAIRE DE SCRAPING =====
const ScrapeForm = ({ onScrape, loading, error }) => {
  const [dates, setDates] = useState({
    date_filter: '',  // Date de publication exacte (optionnelle)
    max_pages: 20
  });

  const handleSubmit = (e) => {
    console.log('📝 Form submitted!', dates);
    e.preventDefault();
    console.log('✅ Validation OK, appel de onScrape');
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
          <Newspaper size={24} color="#10B981" />
          Rechercher des Opportunités RDC MediaCongoWeb
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
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
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
              Date de Publication (optionnelle)
            </label>
            <input
              type="date"
              value={dates.date_filter}
              onChange={(e) => setDates({ ...dates, date_filter: e.target.value })}
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
              <FileText size={16} style={{ display: 'inline', marginRight: '0.5rem', verticalAlign: 'middle' }} />
              Pages Maximum
            </label>
            <input
              type="number"
              value={dates.max_pages}
              onChange={(e) => setDates({ ...dates, max_pages: parseInt(e.target.value) })}
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
          background: '#F0FDF4',
          borderRadius: '10px',
          padding: '1rem',
          marginBottom: '1.5rem',
          border: '2px solid #BBF7D0',
          fontSize: '0.9rem',
          color: '#047857'
        }}>
          ℹ️ Source ID: 337 | Compte: oumayma.dahmani@tunipages.tn | Scraping HTML (API nécessite appname approuvé)
        </div>

        {loading && (
          <div style={{
            background: '#DBEAFE',
            borderRadius: '10px',
            padding: '1rem',
            marginBottom: '1.5rem',
            border: '2px solid #60A5FA',
            fontSize: '0.95rem',
            color: '#1E40AF',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            fontWeight: '600'
          }}>
            <RefreshCw size={20} className="spin" />
            ⏳ Scraping en cours... Veuillez patienter (cela peut prendre jusqu'à 30 secondes)
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            width: '100%',
            padding: '1rem',
            background: loading ? '#94A3B8' : 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
            color: 'white',
            border: 'none',
            borderRadius: '10px',
            fontSize: '1rem',
            fontWeight: '600',
            cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem',
            transition: 'all 0.3s'
          }}
          onMouseEnter={(e) => {
            if (!loading) e.target.style.transform = 'translateY(-2px)';
          }}
          onMouseLeave={(e) => {
            e.target.style.transform = 'translateY(0)';
          }}
        >
          {loading ? (
            <>
              <RefreshCw size={20} className="spin" />
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

// ===== SECTION STATISTIQUES =====
const StatsSection = ({ stats }) => {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
      gap: '1.5rem',
      marginBottom: '2rem'
    }}>
      <div style={{
        background: 'linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%)',
        borderRadius: '16px',
        padding: '1.5rem',
        border: '2px solid #BBF7D0'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
          <div style={{
            background: '#10B981',
            borderRadius: '10px',
            padding: '0.5rem',
            display: 'flex'
          }}>
            <AlertCircle size={24} color="white" />
          </div>
          <span style={{ fontSize: '0.9rem', fontWeight: '600', color: '#064E3B' }}>En attente</span>
        </div>
        <div style={{ fontSize: '2.5rem', fontWeight: '700', color: '#047857' }}>
          {stats.total_pending}
        </div>
      </div>

      <div style={{
        background: 'linear-gradient(135deg, #DCFCE7 0%, #BBF7D0 100%)',
        borderRadius: '16px',
        padding: '1.5rem',
        border: '2px solid #86EFAC'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
          <div style={{
            background: '#16A34A',
            borderRadius: '10px',
            padding: '0.5rem',
            display: 'flex'
          }}>
            <CheckCircle size={24} color="white" />
          </div>
          <span style={{ fontSize: '0.9rem', fontWeight: '600', color: '#14532D' }}>Validées</span>
        </div>
        <div style={{ fontSize: '2.5rem', fontWeight: '700', color: '#15803D' }}>
          {stats.total_validated}
        </div>
      </div>
    </div>
  );
};

// ===== TABLEAU DES OFFRES EN ATTENTE =====
const PendingOffersTable = ({ offers, onValidate, onDelete, onDeleteAll }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [dateFilter, setDateFilter] = useState({ start: '', end: '' });
  const [filteredOffers, setFilteredOffers] = useState(offers);

  useEffect(() => {
    console.log('🔄 useEffect déclenché - Total offers:', offers.length);
    console.log('📋 Premier offer:', offers[0]);

    let filtered = offers;

    // Filtre par recherche textuelle
    if (searchTerm) {
      filtered = filtered.filter(offer =>
        offer.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        offer.promoter?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        offer.reference?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Filtre par date - comparer uniquement YYYY-MM-DD
    if (dateFilter.start || dateFilter.end) {
      console.log('🔍 Filtrage par date activé:', dateFilter);
      console.log('🔍 Exemple de publicationDate du 1er offer:', offers[0]?.publicationDate);

      filtered = filtered.filter(offer => {
        if (!offer.publicationDate) {
          console.log(`⚠️ ${offer.reference}: PAS DE publicationDate`);
          return false;
        }

        // Convertir la date de publication en format YYYY-MM-DD (sans conversion de fuseau horaire)
        const pubDate = new Date(offer.publicationDate);
        const year = pubDate.getFullYear();
        const month = String(pubDate.getMonth() + 1).padStart(2, '0');
        const day = String(pubDate.getDate()).padStart(2, '0');
        const pubDateStr = `${year}-${month}-${day}`; // Format: "2025-12-26"

        let result = true;
        if (dateFilter.start && dateFilter.end) {
          // Vérifier si la date est dans la période [start, end]
          result = pubDateStr >= dateFilter.start && pubDateStr <= dateFilter.end;
          console.log(`${result ? '✅' : '❌'} ${offer.reference}: ${pubDateStr} ${result ? 'DANS' : 'HORS'} période [${dateFilter.start}, ${dateFilter.end}]`);
        } else if (dateFilter.start) {
          // Vérifier si la date est >= start
          result = pubDateStr >= dateFilter.start;
        } else if (dateFilter.end) {
          // Vérifier si la date est <= end
          result = pubDateStr <= dateFilter.end;
        }
        return result;
      });
      console.log(`📊 Après filtrage date: ${filtered.length} offres sur ${offers.length} total`);
    }

    setFilteredOffers(filtered);
  }, [searchTerm, dateFilter, offers]);

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleDateString('fr-FR');
    } catch {
      return dateStr;
    }
  };

  return (
    <div style={{
      background: 'white',
      borderRadius: '16px',
      padding: '2rem',
      boxShadow: '0 4px 12px rgba(0,0,0,0.05)'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1.5rem',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <h3 style={{
          fontSize: '1.25rem',
          fontWeight: '700',
          color: '#0F172A',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <AlertCircle size={24} color="#10B981" />
          Offres en attente ({filteredOffers.length})
        </h3>

        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            onClick={onDeleteAll}
            disabled={!offers.length}
            style={{
              padding: '0.75rem 1.5rem',
              background: !offers.length ? '#94A3B8' : 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '10px',
              fontSize: '0.95rem',
              fontWeight: '600',
              cursor: !offers.length ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              transition: 'all 0.2s'
            }}
          >
            <Trash2 size={16} />
            Supprimer tous
          </button>

          <div style={{ position: 'relative', flex: '1 1 300px', maxWidth: '400px' }}>
            <Search size={20} style={{
              position: 'absolute',
              left: '1rem',
              top: '50%',
              transform: 'translateY(-50%)',
              color: '#94A3B8'
            }} />
            <input
              type="text"
              placeholder="Rechercher par référence, description, promoteur..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                width: '100%',
                padding: '0.75rem 1rem 0.75rem 3rem',
                border: '2px solid #E2E8F0',
                borderRadius: '10px',
                fontSize: '0.9rem'
              }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <label style={{ fontSize: '0.75rem', fontWeight: '600', color: '#64748B' }}>Date début</label>
            <input
              type="date"
              value={dateFilter.start}
              onChange={(e) => {
                console.log('📅 Date début changée:', e.target.value);
                setDateFilter({ ...dateFilter, start: e.target.value });
              }}
              placeholder="Date début"
              style={{
                padding: '0.75rem',
                border: '2px solid #E2E8F0',
                borderRadius: '10px',
                fontSize: '0.9rem',
                minWidth: '150px'
              }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <label style={{ fontSize: '0.75rem', fontWeight: '600', color: '#64748B' }}>Date fin</label>
            <input
              type="date"
              value={dateFilter.end}
              onChange={(e) => {
                console.log('📅 Date fin changée:', e.target.value);
                setDateFilter({ ...dateFilter, end: e.target.value });
              }}
              placeholder="Date fin"
              style={{
                padding: '0.75rem',
                border: '2px solid #E2E8F0',
                borderRadius: '10px',
                fontSize: '0.9rem',
                minWidth: '150px'
              }}
            />
          </div>
        </div>
      </div>

      {filteredOffers.length === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '3rem',
          color: '#64748B',
          background: '#F8FAFC',
          borderRadius: '12px',
          border: '2px dashed #CBD5E1'
        }}>
          <AlertCircle size={48} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
          <p style={{ fontSize: '1.1rem', fontWeight: '600', marginBottom: '0.5rem' }}>
            Aucune offre en attente
          </p>
          <p style={{ fontSize: '0.9rem' }}>
            Lancez un scraping pour extraire de nouvelles offres.
          </p>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{
            width: '100%',
            borderCollapse: 'separate',
            borderSpacing: '0 0.5rem'
          }}>
            <thead>
              <tr style={{
                background: '#F8FAFC',
                fontSize: '0.85rem',
                fontWeight: '600',
                color: '#475569',
                textTransform: 'uppercase',
                letterSpacing: '0.05em'
              }}>
                <th style={{ padding: '1rem', textAlign: 'left', borderRadius: '10px 0 0 10px' }}>Référence</th>
                <th style={{ padding: '1rem', textAlign: 'left' }}>Description</th>
                <th style={{ padding: '1rem', textAlign: 'left' }}>Promoteur</th>
                <th style={{ padding: '1rem', textAlign: 'left' }}>Pays</th>
                <th style={{ padding: '1rem', textAlign: 'left' }}>Date Pub.</th>
                <th style={{ padding: '1rem', textAlign: 'left' }}>Date Exp.</th>
                <th style={{ padding: '1rem', textAlign: 'center', borderRadius: '0 10px 10px 0' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredOffers.map((offer, index) => (
                <tr key={index} style={{
                  background: 'white',
                  borderRadius: '10px',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
                  transition: 'all 0.2s'
                }} onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.08)';
                }} onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.04)';
                }}>
                  <td style={{ padding: '1rem', borderRadius: '10px 0 0 10px' }}>
                    <code style={{
                      background: '#FEF3C7',
                      color: '#92400E',
                      padding: '0.25rem 0.5rem',
                      borderRadius: '6px',
                      fontSize: '0.85rem',
                      fontWeight: '600'
                    }}>
                      {offer.reference}
                    </code>
                  </td>
                  <td style={{ padding: '1rem', maxWidth: '300px' }}>
                    <div style={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      fontWeight: '500',
                      color: '#1E293B'
                    }}>
                      {offer.description}
                    </div>
                  </td>
                  <td style={{ padding: '1rem', color: '#64748B' }}>{offer.promoter || 'N/A'}</td>
                  <td style={{ padding: '1rem', color: '#64748B' }}>{offer.country || 'N/A'}</td>
                  <td style={{ padding: '1rem', color: '#64748B', fontSize: '0.9rem' }}>
                    {formatDate(offer.publicationDate)}
                  </td>
                  <td style={{ padding: '1rem', color: '#64748B', fontSize: '0.9rem' }}>
                    {formatDate(offer.expirationDate)}
                  </td>
                  <td style={{ padding: '1rem', textAlign: 'center', borderRadius: '0 10px 10px 0' }}>
                    <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                      {offer.externalUrl && (
                        <a
                          href={offer.externalUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            padding: '0.5rem',
                            background: '#DBEAFE',
                            color: '#1E40AF',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            textDecoration: 'none'
                          }}
                          title="Voir l'offre"
                        >
                          <ExternalLink size={16} />
                        </a>
                      )}
                      <button
                        onClick={() => onValidate(offer.reference)}
                        style={{
                          padding: '0.5rem 1rem',
                          background: '#DCFCE7',
                          color: '#15803D',
                          border: 'none',
                          borderRadius: '8px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.25rem',
                          fontWeight: '600',
                          fontSize: '0.85rem'
                        }}
                        title="Valider et envoyer"
                      >
                        <CheckCircle size={16} />
                        Valider
                      </button>
                      <button
                        onClick={() => onDelete(offer.reference)}
                        style={{
                          padding: '0.5rem',
                          background: '#FEE2E2',
                          color: '#991B1B',
                          border: 'none',
                          borderRadius: '8px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center'
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
      )}
    </div>
  );
};

// ===== TABLEAU DES OFFRES VALIDÉES =====
const ValidatedOffersTable = ({ offers }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredOffers, setFilteredOffers] = useState(offers);

  useEffect(() => {
    const filtered = offers.filter(offer =>
      offer.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      offer.promoter?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      offer.reference?.toLowerCase().includes(searchTerm.toLowerCase())
    );
    setFilteredOffers(filtered);
  }, [searchTerm, offers]);

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleDateString('fr-FR');
    } catch {
      return dateStr;
    }
  };

  return (
    <div style={{
      background: 'white',
      borderRadius: '16px',
      padding: '2rem',
      boxShadow: '0 4px 12px rgba(0,0,0,0.05)'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1.5rem',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <h3 style={{
          fontSize: '1.25rem',
          fontWeight: '700',
          color: '#0F172A',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <CheckCircle size={24} color="#16A34A" />
          Offres validées ({filteredOffers.length})
        </h3>

        <div style={{ position: 'relative', flex: '1 1 300px', maxWidth: '400px' }}>
          <Search size={20} style={{
            position: 'absolute',
            left: '1rem',
            top: '50%',
            transform: 'translateY(-50%)',
            color: '#94A3B8'
          }} />
          <input
            type="text"
            placeholder="Rechercher..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              padding: '0.75rem 1rem 0.75rem 3rem',
              border: '2px solid #E2E8F0',
              borderRadius: '10px',
              fontSize: '0.9rem'
            }}
          />
        </div>
      </div>

      {filteredOffers.length === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '3rem',
          color: '#64748B',
          background: '#F8FAFC',
          borderRadius: '12px',
          border: '2px dashed #CBD5E1'
        }}>
          <CheckCircle size={48} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
          <p style={{ fontSize: '1.1rem', fontWeight: '600', marginBottom: '0.5rem' }}>
            Aucune offre validée
          </p>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{
            width: '100%',
            borderCollapse: 'separate',
            borderSpacing: '0 0.5rem'
          }}>
            <thead>
              <tr style={{
                background: '#F8FAFC',
                fontSize: '0.85rem',
                fontWeight: '600',
                color: '#475569',
                textTransform: 'uppercase',
                letterSpacing: '0.05em'
              }}>
                <th style={{ padding: '1rem', textAlign: 'left', borderRadius: '10px 0 0 10px' }}>Référence</th>
                <th style={{ padding: '1rem', textAlign: 'left' }}>Description</th>
                <th style={{ padding: '1rem', textAlign: 'left' }}>Promoteur</th>
                <th style={{ padding: '1rem', textAlign: 'left' }}>Pays</th>
                <th style={{ padding: '1rem', textAlign: 'left' }}>Date Valid.</th>
                <th style={{ padding: '1rem', textAlign: 'center', borderRadius: '0 10px 10px 0' }}>Statut</th>
              </tr>
            </thead>
            <tbody>
              {filteredOffers.map((offer, index) => (
                <tr key={index} style={{
                  background: 'white',
                  borderRadius: '10px',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
                  transition: 'all 0.2s'
                }}>
                  <td style={{ padding: '1rem', borderRadius: '10px 0 0 10px' }}>
                    <code style={{
                      background: '#FEF3C7',
                      color: '#92400E',
                      padding: '0.25rem 0.5rem',
                      borderRadius: '6px',
                      fontSize: '0.85rem',
                      fontWeight: '600'
                    }}>
                      {offer.reference}
                    </code>
                  </td>
                  <td style={{ padding: '1rem', maxWidth: '300px' }}>
                    <div style={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      fontWeight: '500',
                      color: '#1E293B'
                    }}>
                      {offer.description}
                    </div>
                  </td>
                  <td style={{ padding: '1rem', color: '#64748B' }}>{offer.promoter || 'N/A'}</td>
                  <td style={{ padding: '1rem', color: '#64748B' }}>{offer.country || 'N/A'}</td>
                  <td style={{ padding: '1rem', color: '#64748B', fontSize: '0.9rem' }}>
                    {formatDate(offer.validationDate)}
                  </td>
                  <td style={{ padding: '1rem', textAlign: 'center', borderRadius: '0 10px 10px 0' }}>
                    <span style={{
                      background: '#DCFCE7',
                      color: '#15803D',
                      padding: '0.4rem 0.8rem',
                      borderRadius: '20px',
                      fontSize: '0.85rem',
                      fontWeight: '600',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.25rem'
                    }}>
                      <CheckCircle size={14} />
                      Validée
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// ===== COMPOSANT PRINCIPAL =====
function MediaCongoPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [pendingOffers, setPendingOffers] = useState([]);
  const [validatedOffers, setValidatedOffers] = useState([]);
  const [activeTab, setActiveTab] = useState('pending');
  const [stats, setStats] = useState({
    total_pending: 0,
    total_validated: 0
  });

  useEffect(() => {
    fetchPending();
    fetchValidated();
  }, []);

  const fetchPending = async () => {
    try {
      const response = await axios.get(`${API_BASE}/pending?limit=1000`);
      if (response.data.success) {
        const offers = response.data.pending.offres || [];
        setPendingOffers(offers);
        setStats(prev => ({ ...prev, total_pending: offers.length }));
      }
    } catch (err) {
      console.error('Erreur chargement pending:', err);
    }
  };

  const fetchValidated = async () => {
    try {
      const response = await axios.get(`${API_BASE}/validated?limit=1000`);
      if (response.data.success) {
        const offers = response.data.validated.offres || [];
        setValidatedOffers(offers);
        setStats(prev => ({ ...prev, total_validated: offers.length }));
      }
    } catch (err) {
      console.error('Erreur chargement validated:', err);
    }
  };

  const handleScrape = async (dates) => {
    console.log('🚀 handleScrape appelé avec:', dates);
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const payload = {
        date_filter: dates.date_filter || null,
        max_pages: dates.max_pages || 20
      };

      console.log('📤 Envoi de la requête POST à:', `${API_BASE}/scrape`);
      console.log('📦 Payload:', payload);

      const response = await axios.post(`${API_BASE}/scrape`, payload);

      console.log('✅ Réponse reçue:', response.data);

      if (response.data.success) {
        const msg = response.data.saved > 0
          ? `✅ Succès! ${response.data.saved} nouvelles offres ajoutées sur ${response.data.total} trouvées`
          : `ℹ️ Scraping terminé: Aucune nouvelle offre (${response.data.total || 0} offres trouvées mais déjà en base)`;
        setSuccess(msg);
        setTimeout(() => {
          fetchPending();
          fetchValidated();
        }, 1000);
      } else {
        setError(`❌ ${response.data.message || 'Échec du scraping'}`);
      }
    } catch (err) {
      console.error('❌ Erreur scraping:', err);
      setError(`❌ Erreur: ${err.response?.data?.message || err.message || 'Impossible de se connecter au serveur'}`);
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async (reference) => {
    try {
      const response = await axios.post(`${API_BASE}/validate/${reference}`);

      if (response.data.success) {
        setSuccess(`✅ ${response.data.message}`);
        setTimeout(() => {
          fetchPending();
          fetchValidated();
        }, 500);
      } else {
        setError(response.data.message || 'Échec de la validation');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Erreur de validation');
    }
  };

  const handleDelete = async (reference) => {
    if (!window.confirm(`Supprimer l'offre ${reference} ?`)) return;

    try {
      const response = await axios.delete(`${API_BASE}/delete/${reference}`);

      if (response.data.success) {
        setSuccess(`🗑️ Offre ${reference} supprimée`);
        fetchPending();
      } else {
        setError('Échec de la suppression');
      }
    } catch (err) {
      setError('Erreur de suppression');
    }
  };

  const handleDeleteAll = async () => {
    if (!window.confirm('⚠️ Êtes-vous sûr de vouloir supprimer toutes les offres en attente ?')) {
      return;
    }

    try {
      const response = await axios.delete(`${API_BASE}/delete_all`);
      if (response.data.success) {
        setSuccess(`✅ ${response.data.message}`);
        fetchPending();
        fetchValidated();
      } else {
        setError(`❌ ${response.data.message}`);
      }
    } catch (err) {
      setError(`❌ Erreur: ${err.response?.data?.message || err.message}`);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #F0FDF4 0%, #FFFFFF 100%)',
      padding: '2rem'
    }}>
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .spin {
          animation: spin 1s linear infinite;
        }
      `}</style>

      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        <div style={{
          background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
          borderRadius: '20px',
          padding: '2rem',
          marginBottom: '2rem',
          color: 'white',
          boxShadow: '0 8px 24px rgba(245, 158, 11, 0.3)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
            <Newspaper size={40} />
            <div>
              <h1 style={{ fontSize: '2rem', fontWeight: '700', margin: 0 }}>
                MediaCongoWeb - Opportunités RDC
              </h1>
              <p style={{ margin: '0.5rem 0 0', opacity: 0.9, fontSize: '0.95rem' }}>
                Extraction automatique des opportunités d'emploi médias et opportunités internationales
              </p>
            </div>
          </div>
        </div>

        {error && (
          <div style={{
            background: '#FEE2E2',
            border: '2px solid #FCA5A5',
            borderRadius: '12px',
            padding: '1rem',
            marginBottom: '1.5rem',
            color: '#991B1B',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            fontSize: '0.95rem'
          }}>
            <AlertCircle size={20} />
            {error}
            <button
              onClick={() => setError('')}
              style={{
                marginLeft: 'auto',
                background: 'none',
                border: 'none',
                color: '#991B1B',
                cursor: 'pointer',
                fontSize: '1.5rem',
                lineHeight: 1
              }}
            >
              ×
            </button>
          </div>
        )}

        {success && (
          <div style={{
            background: '#D1FAE5',
            border: '2px solid #6EE7B7',
            borderRadius: '12px',
            padding: '1rem',
            marginBottom: '1.5rem',
            color: '#065F46',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            fontSize: '0.95rem'
          }}>
            <CheckCircle size={20} />
            {success}
            <button
              onClick={() => setSuccess('')}
              style={{
                marginLeft: 'auto',
                background: 'none',
                border: 'none',
                color: '#065F46',
                cursor: 'pointer',
                fontSize: '1.5rem',
                lineHeight: 1
              }}
            >
              ×
            </button>
          </div>
        )}

        <StatsSection stats={stats} />
        <ScrapeForm onScrape={handleScrape} loading={loading} error={error} />

        <div style={{
          background: 'white',
          borderRadius: '16px',
          padding: '1.5rem 0 0',
          boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
          marginBottom: '2rem'
        }}>
          <div style={{
            display: 'flex',
            gap: '1rem',
            borderBottom: '2px solid #F1F5F9',
            paddingLeft: '1.5rem'
          }}>
            <button
              onClick={() => setActiveTab('pending')}
              style={{
                padding: '1rem 1.5rem',
                background: 'none',
                border: 'none',
                borderBottom: activeTab === 'pending' ? '3px solid #10B981' : '3px solid transparent',
                color: activeTab === 'pending' ? '#10B981' : '#64748B',
                fontWeight: '600',
                cursor: 'pointer',
                fontSize: '1rem',
                transition: 'all 0.2s'
              }}
            >
              📋 En attente ({stats.total_pending})
            </button>
            <button
              onClick={() => setActiveTab('validated')}
              style={{
                padding: '1rem 1.5rem',
                background: 'none',
                border: 'none',
                borderBottom: activeTab === 'validated' ? '3px solid #16A34A' : '3px solid transparent',
                color: activeTab === 'validated' ? '#16A34A' : '#64748B',
                fontWeight: '600',
                cursor: 'pointer',
                fontSize: '1rem',
                transition: 'all 0.2s'
              }}
            >
              ✅ Validées ({stats.total_validated})
            </button>
          </div>
        </div>

        {activeTab === 'pending' && (
          <PendingOffersTable
            offers={pendingOffers}
            onValidate={handleValidate}
            onDelete={handleDelete}
            onDeleteAll={handleDeleteAll}
          />
        )}

        {activeTab === 'validated' && (
          <ValidatedOffersTable offers={validatedOffers} />
        )}
      </div>
    </div>
  );
}

export default MediaCongoPage;
