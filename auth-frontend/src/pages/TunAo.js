// src/pages/TunAo.js - VERSION FINALE CORRIGÉE & OPTIMISÉE AVEC GESTION D'ERREURS AMÉLIORÉE
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import axios from 'axios';
import {
  Search, Calendar, CheckCircle, Edit2, Trash2, RefreshCw, Play,
  AlertCircle, Package, DollarSign, Clock, CheckCircle2, ServerOff
} from 'lucide-react';
import './TunAo.css';

const API_BASE = 'http://localhost:5005/api'; // ⚠️ Port Flask modifié à 5005 (comme dans ton backend)

const arabicStyle = {
  fontFamily: '"Noto Sans Arabic", "Geeza Pro", "Arial Unicode MS", Arial, sans-serif',
  direction: 'rtl',
  textAlign: 'right',
  lineHeight: '1.6',
  unicodeBidi: 'plaintext'
};

// ===== FORMULAIRE DE LANCEMENT SCRAPING =====
const ScrapeForm = ({ onScrape, loading, status, error, backendError }) => {
  const today = new Date().toISOString().split('T')[0];
  const [dates, setDates] = useState({
    start: today,
    end: today
  });
  const [extractionComplete, setExtractionComplete] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    const startDate = new Date(dates.start);
    const endDate = new Date(dates.end);

    if (startDate > endDate) {
      alert("⚠️ La date de début doit être antérieure ou égale à la date de fin.");
      return;
    }

    onScrape({
      start_date: dates.start,
      end_date: dates.end,
      extraction_complete: extractionComplete
    });
  };

  return (
    <div className="card">
      <form onSubmit={handleSubmit} className="scrape-form">
        <h2 className="title">
          <Play size={24} color="#0066CC" />
          Lancer un nouveau Scraping TUNEPS
        </h2>

        {backendError && (
          <div className="alert error">
            <ServerOff size={20} />
            <strong>Erreur Backend :</strong> Impossible de contacter le serveur. Vérifiez si le backend est lancé.
          </div>
        )}

        {status.processing && (
          <div className="alert info">
            <RefreshCw size={20} className="spinning" />
            <strong>Scraping en cours...</strong> ({Math.floor(status.duration)} secondes écoulées). Le scraping est lancé !
          </div>
        )}

        {!status.processing && status.message && (
          <div className="alert success">
            <CheckCircle size={20} />
            {status.message} (Scraping non lancé actuellement)
          </div>
        )}

        {error && (
          <div className="alert error">
            <AlertCircle size={20} />
            {error}
          </div>
        )}

        <div className="grid">
          <div>
            <label><Calendar size={16} /> Date de début</label>
            <input
              type="date"
              value={dates.start}
              onChange={(e) => setDates({ ...dates, start: e.target.value })}
              required
            />
          </div>
          <div>
            <label><Calendar size={16} /> Date de fin</label>
            <input
              type="date"
              value={dates.end}
              onChange={(e) => setDates({ ...dates, end: e.target.value })}
              required
            />
          </div>
        </div>

        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={extractionComplete}
            onChange={(e) => setExtractionComplete(e.target.checked)}
          />
          <span>Mode extraction complète (lots, cautionnements, PDF, images – plus lent)</span>
        </label>

        <button
          type="submit"
          disabled={loading || status.processing || backendError}
          className="btn primary full"
        >
          {loading || status.processing ? (
            <>
              <RefreshCw size={20} className="spinning" />
              Lancement en cours...
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
const PendingList = ({ offres, onValidate, onUpdate, onDelete }) => {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [perPage, setPerPage] = useState(50);

  const filtered = useMemo(() => {
    if (!search) return offres;
    const lower = search.toLowerCase();
    return offres.filter(o =>
      o.reference?.toLowerCase().includes(lower) ||
      o.description?.toLowerCase().includes(lower) ||
      o.promoter?.toLowerCase().includes(lower)
    );
  }, [offres, search]);

  const totalPages = Math.ceil(filtered.length / perPage);
  const paginated = useMemo(() => {
    const start = (page - 1) * perPage;
    return filtered.slice(start, start + perPage);
  }, [filtered, page, perPage]);

  const formatDate = (dateStr) => {
    if (!dateStr || dateStr === 'N/A') return '—';
    return new Date(dateStr).toLocaleString('fr-TN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleValidate = async (ref) => {
    if (!window.confirm(`Valider et publier l'offre ${ref} ?`)) return;
    try {
      const res = await axios.post(`${API_BASE}/validate/${encodeURIComponent(ref)}`);
      if (res.data.success) {
        onValidate(ref);
        alert(`✅ Offre ${ref} validée avec succès !`);
      } else {
        alert(`❌ Échec : ${res.data.message}`);
      }
    } catch (err) {
      alert("❌ Erreur de validation : " + (err.response?.data?.message || err.message));
    }
  };

  const handleUpdateRegion = async (offre) => {
    const newRegion = prompt("Nouvel ID Région (1-28) :", offre.region_id || '');
    if (newRegion === null) return;
    const regionId = parseInt(newRegion.trim());
    if (isNaN(regionId) || regionId < 1 || regionId > 28) {
      alert("⚠️ ID région invalide (doit être entre 1 et 28)");
      return;
    }
    try {
      await axios.post(`${API_BASE}/update/${encodeURIComponent(offre.reference)}`, { region_id: regionId });
      onUpdate(offre.reference, { region_id: regionId });
      alert("✅ Région mise à jour");
    } catch (err) {
      alert("❌ Erreur mise à jour région : " + (err.response?.data?.message || err.message));
    }
  };

  const handleDelete = async (ref) => {
    if (!window.confirm(`Supprimer définitivement l'offre ${ref} ?`)) return;
    try {
      await axios.delete(`${API_BASE}/delete/${encodeURIComponent(ref)}`);
      onDelete(ref);
      alert("🗑️ Offre supprimée");
    } catch (err) {
      alert("❌ Erreur suppression : " + (err.response?.data?.message || err.message));
    }
  };

  return (
    <div className="card">
      <h2 className="title">
        <Clock size={24} color="#FFA500" />
        Offres en Attente de Validation
        <span className="badge orange">{filtered.length}</span>
      </h2>

      <div className="toolbar">
        <div className="search-box">
          <Search size={20} />
          <input
            type="text"
            placeholder="Rechercher par référence, description ou acheteur..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
        <select value={perPage} onChange={(e) => { setPerPage(+e.target.value); setPage(1); }}>
          {[25, 50, 100, 200, 500].map(n => (
            <option key={n} value={n}>{n} par page</option>
          ))}
        </select>
      </div>

      {filtered.length === 0 ? (
        <div className="empty">Aucune offre en attente</div>
      ) : (
        <>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Référence</th>
                  <th>Description</th>
                  <th>Acheteur Public</th>
                  <th>Publication</th>
                  <th>Dernier Délai</th>
                  <th>Lots & Caution</th>
                  <th>Région</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {paginated.map((o) => (
                  <tr key={o.reference}>
                    <td><strong>{o.reference}</strong></td>
                    <td style={arabicStyle}>{o.description?.substring(0, 120) || '—'}...</td>
                    <td style={arabicStyle}>{o.promoter || '—'}</td>
                    <td>{formatDate(o.publicationDate)}</td>
                    <td>{formatDate(o.expirationDate)}</td>
                    <td>
                      {o.lots?.length > 0 ? (
                        <div className="lots-info">
                          <div><Package size={14} /> {o.lots.length} lot{o.lots.length > 1 ? 's' : ''}</div>
                          <div><DollarSign size={14} /> {o.cautionnement_provisoire || '0'} TND</div>
                        </div>
                      ) : (
                        <span style={{ color: '#94A3B8' }}>Pas de lots</span>
                      )}
                    </td>
                    <td>
                      <span className="badge small">{o.region_id || '?'}</span>
                    </td>
                    <td className="actions">
                      <button onClick={() => handleValidate(o.reference)} title="Valider" className="btn success">
                        <CheckCircle size={16} />
                      </button>
                      <button onClick={() => handleUpdateRegion(o)} title="Modifier région" className="btn info">
                        <Edit2 size={16} />
                      </button>
                      <button onClick={() => handleDelete(o.reference)} title="Supprimer" className="btn danger">
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button onClick={() => setPage(1)} disabled={page === 1}>Début</button>
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Précédent</button>
              <span>Page {page} sur {totalPages}</span>
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>Suivant</button>
              <button onClick={() => setPage(totalPages)} disabled={page === totalPages}>Fin</button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

// ===== LISTE DES OFFRES VALIDÉES =====
const ValidatedList = ({ tenders, onRefresh }) => {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const perPage = 50;

  const filtered = useMemo(() => {
    if (!search) return tenders;
    const lower = search.toLowerCase();
    return tenders.filter(t =>
      t.reference?.toLowerCase().includes(lower) ||
      t.description?.toLowerCase().includes(lower)
    );
  }, [tenders, search]);

  const totalPages = Math.ceil(filtered.length / perPage);
  const paginated = filtered.slice((page - 1) * perPage, page * perPage);

  const handleDelete = async (ref) => {
    if (!window.confirm(`Supprimer l'offre validée ${ref} de la base ?`)) return;
    try {
      await axios.delete(`${API_BASE}/tenders/delete/${encodeURIComponent(ref)}`);
      onRefresh();
      alert("🗑️ Offre supprimée");
    } catch (err) {
      alert("❌ Erreur suppression : " + (err.response?.data?.message || err.message));
    }
  };

  const formatDate = (d) => d ? new Date(d).toLocaleDateString('fr-TN') : '—';

  return (
    <div className="card">
      <h2 className="title">
        <CheckCircle2 size={24} color="#22C55E" />
        Offres Validées & Publiées
        <span className="badge green">{filtered.length}</span>
      </h2>

      <div className="toolbar">
        <div className="search-box">
          <Search size={20} />
          <input
            type="text"
            placeholder="Rechercher..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="empty">Aucune offre validée pour le moment</div>
      ) : (
        <>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Référence</th>
                  <th>Description</th>
                  <th>Acheteur</th>
                  <th>Publication</th>
                  <th>Dernier Délai</th>
                  <th>Validée le</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {paginated.map((t) => (
                  <tr key={t.reference}>
                    <td><strong>{t.reference}</strong></td>
                    <td style={arabicStyle}>{(t.description || '').substring(0, 120)}...</td>
                    <td style={arabicStyle}>{t.promoter || '—'}</td>
                    <td>{formatDate(t.publicationDate)}</td>
                    <td>{formatDate(t.expirationDate)}</td>
                    <td>{formatDate(t.validationDate)}</td>
                    <td className="actions">
                      <button onClick={() => handleDelete(t.reference)} className="btn danger">
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button onClick={() => setPage(1)} disabled={page === 1}>Début</button>
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Précédent</button>
              <span>Page {page} / {totalPages}</span>
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>Suivant</button>
              <button onClick={() => setPage(totalPages)} disabled={page === totalPages}>Fin</button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

// ===== PAGE PRINCIPALE =====
const TunAo = () => {
  const [pending, setPending] = useState([]);
  const [validated, setValidated] = useState([]);
  const [status, setStatus] = useState({ processing: false, duration: 0, message: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [backendError, setBackendError] = useState(false);

  const fetchPending = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/pending?limit=2000`);
      if (res.data.success && res.data.pending?.offres) {
        setPending(res.data.pending.offres);
      }
    } catch (err) {
      console.error("Erreur chargement pending :", err);
    }
  }, []);

  const fetchValidated = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/tenders`);
      if (res.data.success) {
        setValidated(res.data.tenders || []);
      }
    } catch (err) {
      console.error("Erreur chargement validées :", err);
    }
  }, []);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/status`);
      setStatus({
        processing: res.data.processing,
        duration: res.data.duration_seconds || 0,
        message: res.data.message || ''
      });
      setBackendError(false);
    } catch (err) {
      setStatus({ processing: false, duration: 0, message: '' });
      setBackendError(true);
    }
  }, []);

  const handleScrape = async (params) => {
    setLoading(true);
    setError('');
    try {
      await axios.post(`${API_BASE}/scrape`, params);
      alert('🚀 Scraping lancé avec succès ! Les nouvelles offres apparaîtront bientôt.');
      fetchStatus();
    } catch (err) {
      setError(err.response?.data?.error || "Impossible de contacter le serveur backend. Vérifiez si le scraping est lancé.");
    } finally {
      setLoading(false);
    }
  };

  const refreshAll = () => {
    fetchPending();
    fetchValidated();
    fetchStatus();
  };

  useEffect(() => {
    refreshAll();

    const interval = setInterval(() => {
      fetchStatus();
      if (!status.processing) {
        fetchPending();
      }
    }, 8000);

    return () => clearInterval(interval);
  }, [fetchPending, fetchStatus, status.processing]);

  return (
    <div className="page tunao-page">
      <div className="container">
        <header className="header">
          <h1>🇹🇳 Gestion des Appels d’Offres TUNEPS</h1>
          <p>Scraping, validation et publication automatique vers appeloffres.net</p>
        </header>

        <div className="stats-bar">
          <div className="stats">
            <span><strong>{pending.length}</strong> offres en attente</span>
            <span>•</span>
            <span><strong>{validated.length}</strong> offres publiées</span>
          </div>
          <button onClick={refreshAll} className="btn primary">
            <RefreshCw size={18} />
            Rafraîchir tout
          </button>
        </div>

        <ScrapeForm onScrape={handleScrape} loading={loading} status={status} error={error} backendError={backendError} />

        <PendingList
          offres={pending}
          onValidate={(ref) => {
            setPending(prev => prev.filter(o => o.reference !== ref));
            fetchValidated();
          }}
          onUpdate={(ref, data) => {
            setPending(prev => prev.map(o => o.reference === ref ? { ...o, ...data } : o));
          }}
          onDelete={(ref) => setPending(prev => prev.filter(o => o.reference !== ref))}
        />

        <ValidatedList tenders={validated} onRefresh={fetchValidated} />
      </div>
    </div>
  );
};

export default TunAo;