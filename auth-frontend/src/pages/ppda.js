// src/pages/PPDA.js - Page pour PPDA Malawi
import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { Search, Calendar, CheckCircle, Edit2, Trash2, RefreshCw, Play, AlertCircle, Globe, Send, FileText, ExternalLink } from 'lucide-react';
import './MediaCongo.css';

const API_BASE = '/api/ppda';

// ===== FORMULAIRE DE SCRAPING =====
const ScrapeForm = ({ onScrape, loading, error }) => {
  const [dates, setDates] = useState({
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    max_pages: 10
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
          <Globe size={24} color="#10B981" />
          Rechercher des Opportunités PPDA Malawi
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
              Date Début (optionnel)
            </label>
            <input
              type="date"
              value={dates.start}
              onChange={(e) => setDates({ ...dates, start: e.target.value })}
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
              Pages Max
            </label>
            <input
              type="number"
              value={dates.max_pages}
              onChange={(e) => setDates({ ...dates, max_pages: parseInt(e.target.value) })}
              min="1"
              max="50"
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

        <button
          type="submit"
          disabled={loading}
          style={{
            width: '100%',
            padding: '1rem',
            background: loading ? '#94A3B8' : 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
            color: 'white',
            border: 'none',
            borderRadius: '12px',
            fontSize: '1rem',
            fontWeight: '600',
            cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.75rem',
            transition: 'all 0.3s',
            boxShadow: loading ? 'none' : '0 4px 12px rgba(16, 185, 129, 0.3)'
          }}
        >
          {loading ? (
            <>
              <RefreshCw className="animate-spin" size={20} />
              Extraction en cours...
            </>
          ) : (
            <>
              <Play size={20} />
              Lancer l'extraction
            </>
          )}
        </button>
      </form>
    </div>
  );
};

// ===== TABLEAU DES RÉSULTATS =====
const TendersTable = ({ tenders, onRefresh, loading, stats, onValidate, onValidateAll, onDeleteAll }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [validatingRef, setValidatingRef] = useState(null);
  const [validatingAll, setValidatingAll] = useState(false);

  const filteredTenders = useMemo(() => {
    if (!searchTerm) return tenders;
    const term = searchTerm.toLowerCase();
    return tenders.filter(t =>
      t.reference?.toLowerCase().includes(term) ||
      t.title?.toLowerCase().includes(term) ||
      t.description?.toLowerCase().includes(term) ||
      t.promoter?.toLowerCase().includes(term)
    );
  }, [tenders, searchTerm]);

  const handleValidate = async (tender) => {
    setValidatingRef(tender.reference);
    await onValidate(tender);
    setValidatingRef(null);
  };

  const handleValidateAll = async () => {
    setValidatingAll(true);
    await onValidateAll();
    setValidatingAll(false);
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
        <h2 style={{
          fontSize: '1.5rem',
          fontWeight: '700',
          color: '#0F172A',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem'
        }}>
          <FileText size={24} color="#10B981" />
          Appels d'Offres PPDA ({filteredTenders.length})
        </h2>

        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          {stats && (
            <div style={{
              display: 'flex',
              gap: '1rem',
              padding: '0.5rem 1rem',
              background: '#F1F5F9',
              borderRadius: '8px',
              fontSize: '0.85rem'
            }}>
              <span><strong>Total:</strong> {stats.total || 0}</span>
              <span><strong>En attente:</strong> {stats.pending || 0}</span>
              <span style={{ color: '#10B981' }}><strong>Validés:</strong> {stats.validated || 0}</span>
              <span style={{ color: '#EF4444' }}><strong>Échecs:</strong> {stats.failed || 0}</span>
            </div>
          )}
          <button
            onClick={handleValidateAll}
            disabled={validatingAll || !tenders.length}
            style={{
              padding: '0.75rem 1.5rem',
              background: validatingAll ? '#94A3B8' : 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '10px',
              fontSize: '0.95rem',
              fontWeight: '600',
              cursor: validatingAll || !tenders.length ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              transition: 'all 0.2s'
            }}
          >
            {validatingAll ? (
              <>
                <RefreshCw className="animate-spin" size={16} />
                Validation...
              </>
            ) : (
              <>
                <Send size={16} />
                Valider tout
              </>
            )}
          </button>
          <button
            onClick={onDeleteAll}
            disabled={!tenders.length}
            style={{
              padding: '0.75rem 1.5rem',
              background: !tenders.length ? '#94A3B8' : 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '10px',
              fontSize: '0.95rem',
              fontWeight: '600',
              cursor: !tenders.length ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              transition: 'all 0.2s'
            }}
          >
            <AlertCircle size={16} />
            Supprimer tous
          </button>
          <button
            onClick={onRefresh}
            disabled={loading}
            style={{
              padding: '0.75rem 1.5rem',
              background: loading ? '#94A3B8' : '#F1F5F9',
              color: '#475569',
              border: 'none',
              borderRadius: '10px',
              fontSize: '0.95rem',
              fontWeight: '600',
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              transition: 'all 0.2s'
            }}
          >
            <RefreshCw className={loading ? 'animate-spin' : ''} size={16} />
            Actualiser
          </button>
        </div>
      </div>

      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ position: 'relative' }}>
          <Search
            size={20}
            style={{
              position: 'absolute',
              left: '1rem',
              top: '50%',
              transform: 'translateY(-50%)',
              color: '#94A3B8'
            }}
          />
          <input
            type="text"
            placeholder="Rechercher par référence, titre, promoteur..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              padding: '0.75rem 1rem 0.75rem 3rem',
              border: '2px solid #E2E8F0',
              borderRadius: '10px',
              fontSize: '0.95rem',
              transition: 'all 0.2s'
            }}
          />
        </div>
      </div>

      {filteredTenders.length === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '3rem',
          color: '#94A3B8',
          fontSize: '1rem'
        }}>
          <FileText size={48} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
          <p>Aucun appel d'offres trouvé</p>
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
                color: '#64748B',
                textTransform: 'uppercase',
                letterSpacing: '0.05em'
              }}>
                <th style={{ padding: '1rem', textAlign: 'left', borderRadius: '8px 0 0 8px' }}>Référence</th>
                <th style={{ padding: '1rem', textAlign: 'left' }}>Titre</th>
                <th style={{ padding: '1rem', textAlign: 'left' }}>Promoteur</th>
                <th style={{ padding: '1rem', textAlign: 'left' }}>Publication</th>
                <th style={{ padding: '1rem', textAlign: 'left' }}>Expiration</th>
                <th style={{ padding: '1rem', textAlign: 'center' }}>Document</th>
                <th style={{ padding: '1rem', textAlign: 'center' }}>Statut</th>
                <th style={{ padding: '1rem', textAlign: 'center', borderRadius: '0 8px 8px 0' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredTenders.map((tender, idx) => (
                <tr
                  key={tender.id || idx}
                  style={{
                    background: 'white',
                    transition: 'all 0.2s',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                    borderRadius: '8px'
                  }}
                >
                  <td style={{
                    padding: '1rem',
                    fontWeight: '600',
                    color: '#0F172A',
                    borderRadius: '8px 0 0 8px'
                  }}>
                    {tender.reference}
                  </td>
                  <td style={{
                    padding: '1rem',
                    color: '#475569',
                    maxWidth: '300px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                  }} title={tender.title}>
                    {tender.title || 'N/A'}
                  </td>
                  <td style={{ padding: '1rem', color: '#475569' }}>
                    {tender.promoter || 'N/A'}
                  </td>
                  <td style={{ padding: '1rem', color: '#475569', fontSize: '0.9rem' }}>
                    {tender.publication_date || 'N/A'}
                  </td>
                  <td style={{ padding: '1rem', color: '#475569', fontSize: '0.9rem' }}>
                    {tender.expiration_date || 'N/A'}
                  </td>
                  <td style={{ padding: '1rem', textAlign: 'center' }}>
                    {tender.document_url ? (
                      <a
                        href={tender.document_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.25rem',
                          color: '#3B82F6',
                          textDecoration: 'none',
                          fontSize: '0.85rem'
                        }}
                      >
                        <ExternalLink size={14} />
                        PDF
                      </a>
                    ) : (
                      <span style={{ color: '#94A3B8', fontSize: '0.85rem' }}>-</span>
                    )}
                  </td>
                  <td style={{ padding: '1rem', textAlign: 'center' }}>
                    <span style={{
                      padding: '0.4rem 0.8rem',
                      borderRadius: '6px',
                      fontSize: '0.8rem',
                      fontWeight: '600',
                      background: tender.status === 'validated' ? '#D1FAE5' : tender.status === 'failed' ? '#FEE2E2' : '#FEF3C7',
                      color: tender.status === 'validated' ? '#065F46' : tender.status === 'failed' ? '#991B1B' : '#92400E'
                    }}>
                      {tender.status === 'validated' ? 'Validé' : tender.status === 'failed' ? 'Échec' : 'En attente'}
                    </span>
                  </td>
                  <td style={{
                    padding: '1rem',
                    textAlign: 'center',
                    borderRadius: '0 8px 8px 0'
                  }}>
                    <button
                      onClick={() => handleValidate(tender)}
                      disabled={validatingRef === tender.reference || tender.status === 'validated'}
                      style={{
                        padding: '0.5rem 1rem',
                        background: tender.status === 'validated' ? '#94A3B8' : '#10B981',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '0.85rem',
                        fontWeight: '600',
                        cursor: tender.status === 'validated' ? 'not-allowed' : 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.25rem',
                        transition: 'all 0.2s'
                      }}
                    >
                      {validatingRef === tender.reference ? (
                        <>
                          <RefreshCw className="animate-spin" size={14} />
                          Envoi...
                        </>
                      ) : (
                        <>
                          <Send size={14} />
                          Valider
                        </>
                      )}
                    </button>
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
const PPDA = () => {
  const [tenders, setTenders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [stats, setStats] = useState(null);

  const fetchTenders = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE}/tenders?status=all&limit=100`);
      if (response.data.success) {
        setTenders(response.data.tenders);
      }
    } catch (err) {
      console.error('Erreur chargement tenders:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_BASE}/stats`);
      if (response.data.success) {
        setStats(response.data.stats);
      }
    } catch (err) {
      console.error('Erreur chargement stats:', err);
    }
  };

  useEffect(() => {
    fetchTenders();
    fetchStats();
  }, []);

  const handleScrape = async (dates) => {
    console.log('🚀 handleScrape called with:', dates);
    try {
      setLoading(true);
      setError('');

      const payload = {
        start_date: dates.start || null,
        max_pages: dates.max_pages || 10
      };

      console.log('📤 Sending to API:', payload);

      const response = await axios.post(`${API_BASE}/scrape`, payload, {
        timeout: 120000
      });

      console.log('📥 API Response:', response.data);

      if (response.data.success) {
        alert(`✅ ${response.data.message}\n\nStats:\n- Total: ${response.data.stats.total}\n- Nouveaux: ${response.data.stats.saved}\n- Doublons: ${response.data.stats.duplicates}`);
        await fetchTenders();
        await fetchStats();
      } else {
        setError(response.data.message || 'Erreur lors du scraping');
      }
    } catch (err) {
      console.error('❌ Erreur scraping:', err);
      setError(err.response?.data?.message || err.message || 'Erreur lors du scraping');
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async (tender) => {
    try {
      const response = await axios.post(`${API_BASE}/validate`);
      if (response.data.success) {
        alert(`✅ ${response.data.message}`);
        await fetchTenders();
        await fetchStats();
      }
    } catch (err) {
      alert(`❌ Erreur: ${err.response?.data?.message || err.message}`);
    }
  };

  const handleValidateAll = async () => {
    try {
      const response = await axios.post(`${API_BASE}/validate`);
      if (response.data.success) {
        alert(`✅ ${response.data.message}\n\nStats:\n- Total: ${response.data.stats.total}\n- Réussis: ${response.data.stats.success}\n- Échecs: ${response.data.stats.failed}`);
        await fetchTenders();
        await fetchStats();
      }
    } catch (err) {
      alert(`❌ Erreur: ${err.response?.data?.message || err.message}`);
    }
  };

  const handleDeleteAll = async () => {
    if (!window.confirm('⚠️ Êtes-vous sûr de vouloir supprimer tous les appels d\'offres en attente ?')) {
      return;
    }

    try {
      const response = await axios.post(`${API_BASE}/delete_all`);
      if (response.data.success) {
        alert(`✅ ${response.data.message}`);
        await fetchTenders();
        await fetchStats();
      } else {
        alert(`❌ ${response.data.message}`);
      }
    } catch (err) {
      alert(`❌ Erreur: ${err.response?.data?.message || err.message}`);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #F0FDF4 0%, #FFFFFF 100%)',
      padding: '2rem'
    }}>
      <div style={{
        maxWidth: '1400px',
        margin: '0 auto'
      }}>
        <div style={{
          background: 'white',
          borderRadius: '16px',
          padding: '2rem',
          marginBottom: '2rem',
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
        }}>
          <h1 style={{
            fontSize: '2rem',
            fontWeight: '800',
            color: '#0F172A',
            marginBottom: '0.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '1rem'
          }}>
            <Globe size={32} color="#10B981" />
            PPDA Malawi - Public Procurement
          </h1>
          <p style={{
            color: '#64748B',
            fontSize: '1rem'
          }}>
            Extraction automatique des appels d'offres depuis le portail PPDA Malawi
          </p>
        </div>

        <ScrapeForm onScrape={handleScrape} loading={loading} error={error} />
        <TendersTable
          tenders={tenders}
          onRefresh={fetchTenders}
          loading={loading}
          stats={stats}
          onValidate={handleValidate}
          onValidateAll={handleValidateAll}
          onDeleteAll={handleDeleteAll}
        />
      </div>
    </div>
  );
};

export default PPDA;
