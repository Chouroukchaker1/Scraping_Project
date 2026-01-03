// src/pages/armp.js - Scraper ARMP Madagascar
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import axios from 'axios';
import {
  Search, Calendar, CheckCircle, Edit2, Trash2, RefreshCw, Play,
  AlertCircle, Package, DollarSign
} from 'lucide-react';
import './armp.css';

const API_BASE = '/api/armp/api';

const arabicStyle = {
  fontFamily: '"Noto Sans Arabic", "Arial Unicode MS", Tahoma, Arial, sans-serif',
  direction: 'auto',
  textAlign: 'right',
  whiteSpace: 'pre-wrap',
  unicodeBidi: 'plaintext'
};

// ===== FORMULAIRE DE SCRAPING =====
const ScrapeForm = ({ onScrape, loading, status, error }) => {
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
    <div className="card">
      <form onSubmit={handleSubmit}>
        <h2 className="title">
          <Search size={24} color="#0066CC" />
          Lancer un nouveau Scraping
        </h2>

        {status.processing && (
          <div className="alert warning">
            <RefreshCw size={20} className="spinning" />
            Scraping en cours depuis {status.duration?.toFixed(0)} secondes...
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
            <label><Calendar size={16} /> Date Début</label>
            <input type="date" value={dates.start} onChange={e => setDates({ ...dates, start: e.target.value })} required />
          </div>
          <div>
            <label><Calendar size={16} /> Date Fin</label>
            <input type="date" value={dates.end} onChange={e => setDates({ ...dates, end: e.target.value })} required />
          </div>
        </div>

        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={extractionComplete}
            onChange={e => setExtractionComplete(e.target.checked)}
          />
          <span>Mode extraction complète (lots, cautionnements, PDF – plus lent)</span>
        </label>

        <button type="submit" disabled={loading || status.processing} className="btn primary full">
          {loading ? (
            <> <RefreshCw size={20} className="spinning" /> Lancement en cours... </>
          ) : (
            <> <Play size={20} /> Lancer le Scraping </>
          )}
        </button>
      </form>
    </div>
  );
};

// ===== LISTE DES OFFRES EN ATTENTE =====
const PendingList = ({ offres, onValidate, onUpdate, onDelete, onDateFilterChange }) => {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [perPage, setPerPage] = useState(50);
  const [dateFilter, setDateFilter] = useState({ start: '', end: '' });

  // Déclencher le changement de filtre de date vers le parent
  const handleDateChange = (newFilter) => {
    setDateFilter(newFilter);
    setPage(1);
    if (onDateFilterChange) {
      onDateFilterChange(newFilter);
    }
  };

  const filtered = useMemo(() => {
    return offres.filter(o => {
      // Filtre par texte uniquement (les dates sont filtrées côté backend)
      const matchText = o.reference?.toLowerCase().includes(search.toLowerCase()) ||
        o.description?.toLowerCase().includes(search.toLowerCase()) ||
        o.promoter?.toLowerCase().includes(search.toLowerCase());

      return matchText;
    });
  }, [offres, search]);

  const totalPages = Math.ceil(filtered.length / perPage);
  const paginated = useMemo(() => {
    const start = (page - 1) * perPage;
    return filtered.slice(start, start + perPage);
  }, [filtered, page, perPage]);

  const formatDate = (d) => d && d !== 'N/A' ? new Date(d).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : 'N/A';

  const handleValidate = async (ref) => {
    if (!window.confirm(`Valider l'offre ${ref} ?`)) return;
    try {
      const res = await axios.post(`${API_BASE}/validate/${encodeURIComponent(ref)}`);
      if (res.data.success) {
        onValidate(ref);
        alert(`✅ Offre ${ref} validée !`);
      }
    } catch (err) {
      alert("❌ Erreur validation : " + (err.response?.data?.message || err.message));
    }
  };

  const handleUpdate = async (offre) => {
    const region = prompt("ID Région (1-28) :", offre.region_id || '');
    if (region !== null && region.trim() !== '') {
      try {
        await axios.post(`${API_BASE}/update/${encodeURIComponent(offre.reference)}`, { region_id: parseInt(region) });
        onUpdate(offre.reference, { region_id: parseInt(region) });
      } catch (err) {
        alert("❌ Erreur mise à jour");
      }
    }
  };

  const handleDelete = async (ref) => {
    if (!window.confirm(`Supprimer l'offre ${ref} ?`)) return;
    try {
      await axios.delete(`${API_BASE}/delete/${encodeURIComponent(ref)}`);
      onDelete(ref);
    } catch (err) {
      alert("❌ Erreur suppression");
    }
  };

  const handleDeleteAll = async () => {
    if (!window.confirm(`⚠️ ATTENTION: Supprimer TOUTES les ${offres.length} offres en attente ?\n\nCette action est irréversible!`)) return;
    try {
      await axios.delete(`${API_BASE}/delete-all`);
      alert(`✅ ${offres.length} offres supprimées avec succès`);
      onDelete(null); // Trigger parent refresh
      window.location.reload();
    } catch (err) {
      alert("❌ Erreur suppression : " + (err.response?.data?.message || err.message));
    }
  };

  return (
    <div className="card">
      <h2 className="title">
        ⏳ Offres en Attente <span className="badge blue">{filtered.length}</span>
      </h2>

      <div className="toolbar">
        <div className="search-box">
          <Search size={20} />
          <input
            type="text"
            placeholder="Rechercher référence, description, acheteur..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
        <select value={perPage} onChange={e => { setPerPage(+e.target.value); setPage(1); }}>
          {[10, 25, 50, 100, 200].map(n => <option key={n} value={n}>{n} / page</option>)}
        </select>
        {offres.length > 0 && (
          <button onClick={handleDeleteAll} className="btn danger" style={{ marginLeft: '0.5rem' }}>
            <Trash2 size={18} /> Supprimer Tout
          </button>
        )}
      </div>

      <div className="toolbar" style={{ marginTop: '1rem', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Calendar size={16} />
          <label style={{ fontSize: '0.9rem', fontWeight: '600' }}>Date de publication:</label>
          <input
            type="date"
            value={dateFilter.start}
            onChange={e => handleDateChange({ ...dateFilter, start: e.target.value })}
            placeholder="Du"
            style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid #E2E8F0' }}
          />
          <span>→</span>
          <input
            type="date"
            value={dateFilter.end}
            onChange={e => handleDateChange({ ...dateFilter, end: e.target.value })}
            placeholder="Au"
            style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid #E2E8F0' }}
          />
          {(dateFilter.start || dateFilter.end) && (
            <button
              onClick={() => handleDateChange({ start: '', end: '' })}
              className="btn"
              style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
            >
              Réinitialiser
            </button>
          )}
        </div>
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
                  <th>Acheteur</th>
                  <th>Publiée</th>
                  <th>Limite</th>
                  <th>Lots / Caution</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {paginated.map(o => (
                  <tr key={o.reference}>
                    <td><strong>{o.reference}</strong></td>
                    <td style={arabicStyle}>{(o.description || '').substring(0, 100)}...</td>
                    <td style={arabicStyle}>{o.promoter}</td>
                    <td>{formatDate(o.publicationDate)}</td>
                    <td>{formatDate(o.expirationDate)}</td>
                    <td>
                      {o.lots && o.lots.length > 0 ? (
                        <div style={{ fontSize: '0.85rem' }}>
                          <Package size={14} style={{ display: 'inline', marginRight: '4px' }} />
                          {o.lots.length} lot{o.lots.length > 1 ? 's' : ''}
                          <br />
                          <DollarSign size={14} style={{ display: 'inline', marginRight: '4px' }} />
                          {o.cautionnement_provisoire || '0'}
                        </div>
                      ) : (
                        <span style={{ color: '#94A3B8' }}>—</span>
                      )}
                    </td>
                    <td className="actions">
                      <button onClick={() => handleValidate(o.reference)} title="Valider" className="btn success"><CheckCircle size={16} /></button>
                      <button onClick={() => handleUpdate(o)} title="Modifier région" className="btn info"><Edit2 size={16} /></button>
                      <button onClick={() => handleDelete(o.reference)} title="Supprimer" className="btn danger"><Trash2 size={16} /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button onClick={() => setPage(1)} disabled={page === 1}>⏮️</button>
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>⬅️</button>
              <span>Page {page} / {totalPages}</span>
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>➡️</button>
              <button onClick={() => setPage(totalPages)} disabled={page === totalPages}>⏭️</button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

// ===== LISTE DES OFFRES VALIDÉES =====
const ValidatedList = ({ tenders, onRefresh, onDateFilterChange }) => {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [perPage] = useState(50);
  const [dateFilter, setDateFilter] = useState({ start: '', end: '' });

  // Déclencher le changement de filtre de date vers le parent
  const handleDateChange = (newFilter) => {
    setDateFilter(newFilter);
    setPage(1);
    if (onDateFilterChange) {
      onDateFilterChange(newFilter);
    }
  };

  const filtered = useMemo(() => tenders.filter(t => {
    // Filtre par texte uniquement (les dates sont filtrées côté backend)
    const matchText = t.reference?.toLowerCase().includes(search.toLowerCase()) ||
      t.description?.toLowerCase().includes(search.toLowerCase());

    return matchText;
  }), [tenders, search]);

  const totalPages = Math.ceil(filtered.length / perPage);
  const paginated = useMemo(() => {
    const start = (page - 1) * perPage;
    return filtered.slice(start, start + perPage);
  }, [filtered, page, perPage]);

  const handleDelete = async (ref) => {
    if (!window.confirm(`Supprimer l'offre validée ${ref} ?`)) return;
    try {
      await axios.delete(`${API_BASE}/tenders/delete/${encodeURIComponent(ref)}`);
      onRefresh();
    } catch (err) {
      alert("❌ Erreur suppression");
    }
  };

  const handleDeleteAll = async () => {
    if (!window.confirm(`⚠️ ATTENTION: Supprimer TOUTES les ${tenders.length} offres validées ?\n\nCette action est irréversible!`)) return;
    try {
      await axios.delete(`${API_BASE}/tenders/delete-all`);
      alert(`✅ ${tenders.length} offres validées supprimées avec succès`);
      onRefresh();
      window.location.reload();
    } catch (err) {
      alert("❌ Erreur suppression : " + (err.response?.data?.message || err.message));
    }
  };

  const formatDate = (d) => d ? new Date(d).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : 'N/A';

  return (
    <div className="card">
      <h2 className="title">
        ✅ Offres Validées <span className="badge green">{filtered.length}</span>
      </h2>

      <div className="toolbar">
        <div className="search-box">
          <Search size={20} />
          <input
            type="text"
            placeholder="Rechercher..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
        <button onClick={handleDeleteAll} className="btn danger" style={{ marginLeft: '0.5rem' }}>
          <Trash2 size={18} /> Supprimer Tout
        </button>
      </div>

      <div className="toolbar" style={{ marginTop: '1rem', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Calendar size={16} />
          <label style={{ fontSize: '0.9rem', fontWeight: '600' }}>Date de publication:</label>
          <input
            type="date"
            value={dateFilter.start}
            onChange={e => handleDateChange({ ...dateFilter, start: e.target.value })}
            placeholder="Du"
            style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid #E2E8F0' }}
          />
          <span>→</span>
          <input
            type="date"
            value={dateFilter.end}
            onChange={e => handleDateChange({ ...dateFilter, end: e.target.value })}
            placeholder="Au"
            style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid #E2E8F0' }}
          />
          {(dateFilter.start || dateFilter.end) && (
            <button
              onClick={() => handleDateChange({ start: '', end: '' })}
              className="btn"
              style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
            >
              Réinitialiser
            </button>
          )}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="empty">Aucune offre validée</div>
      ) : (
        <>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Référence</th>
                  <th>Description</th>
                  <th>Acheteur</th>
                  <th>Publiée</th>
                  <th>Limite</th>
                  <th>Validée le</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {paginated.map(t => (
                  <tr key={t.reference}>
                    <td><strong>{t.reference}</strong></td>
                    <td style={arabicStyle}>{(t.description || '').substring(0, 100)}...</td>
                    <td style={arabicStyle}>{t.promoter}</td>
                    <td>{formatDate(t.publicationDate)}</td>
                    <td>{formatDate(t.expirationDate)}</td>
                    <td>{t.validationDate ? new Date(t.validationDate).toLocaleDateString('fr-FR') : '—'}</td>
                    <td className="actions">
                      <button onClick={() => handleDelete(t.reference)} className="btn danger"><Trash2 size={16} /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button onClick={() => setPage(1)} disabled={page === 1}>⏮️</button>
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>⬅️</button>
              <span>Page {page} / {totalPages}</span>
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>➡️</button>
              <button onClick={() => setPage(totalPages)} disabled={page === totalPages}>⏭️</button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

// ===== PAGE PRINCIPALE =====
const Armp = () => {
  const [pending, setPending] = useState([]);
  const [validated, setValidated] = useState([]);
  const [status, setStatus] = useState({ processing: false, duration: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [pendingDateFilter, setPendingDateFilter] = useState({ start: '', end: '' });
  const [validatedDateFilter, setValidatedDateFilter] = useState({ start: '', end: '' });

  const fetchPending = useCallback(async (dateFilter) => {
    try {
      let url = `${API_BASE}/pending?limit=1000`;
      if (dateFilter && dateFilter.start) url += `&date_start=${dateFilter.start}`;
      if (dateFilter && dateFilter.end) url += `&date_end=${dateFilter.end}`;

      const res = await axios.get(url);
      setPending(res.data.offres || []);
    } catch (err) {
      console.error(err);
    }
  }, []);

  const fetchValidated = useCallback(async (dateFilter) => {
    try {
      let url = `${API_BASE}/tenders`;
      const params = [];
      if (dateFilter && dateFilter.start) params.push(`date_start=${dateFilter.start}`);
      if (dateFilter && dateFilter.end) params.push(`date_end=${dateFilter.end}`);
      if (params.length > 0) url += `?${params.join('&')}`;

      const res = await axios.get(url);
      setValidated(res.data.offres || res.data.tenders || []);
    } catch (err) {
      console.error(err);
    }
  }, []);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/status`);
      setStatus({
        processing: res.data.processing,
        duration: res.data.duration_seconds || 0
      });
    } catch (err) {
      setStatus({ processing: false, duration: 0 });
    }
  }, []);

  const handleScrape = async (params) => {
    setLoading(true);
    setError('');
    try {
      await axios.post(`${API_BASE}/scrape`, params);
      alert('Scraping lancé ! Rafraîchissez dans quelques dizaines de secondes.');
      fetchStatus();
    } catch (err) {
      setError(err.response?.data?.error || "Erreur de connexion au backend");
    } finally {
      setLoading(false);
    }
  };

  const handlePendingDateFilter = useCallback((dateFilter) => {
    setPendingDateFilter(dateFilter);
    fetchPending(dateFilter);
  }, [fetchPending]);

  const handleValidatedDateFilter = useCallback((dateFilter) => {
    setValidatedDateFilter(dateFilter);
    fetchValidated(dateFilter);
  }, [fetchValidated]);

  const refreshAll = useCallback(() => {
    // Use a ref or get the latest filter values
    setPendingDateFilter(prev => {
      fetchPending(prev);
      return prev;
    });
    setValidatedDateFilter(prev => {
      fetchValidated(prev);
      return prev;
    });
    fetchStatus();
  }, [fetchPending, fetchValidated, fetchStatus]);

  useEffect(() => {
    // Initial load only
    fetchPending({ start: '', end: '' });
    fetchValidated({ start: '', end: '' });
    fetchStatus();

    const interval = setInterval(() => {
      fetchStatus();
    }, 10000);
    return () => clearInterval(interval);
  }, [fetchPending, fetchValidated, fetchStatus]);

  return (
    <div className="page">
      <div className="container">
        <header className="header">
          <h1>🇲🇬 Scraper ARMP – Madagascar</h1>
          <p>Extraction et validation automatique depuis armp.mg</p>
        </header>

        <div className="stats">
          <div>
            <strong>{pending.length}</strong> en attente • <strong>{validated.length}</strong> validées
          </div>
          <button onClick={refreshAll} className="btn primary">
            <RefreshCw size={18} /> Rafraîchir
          </button>
        </div>

        <ScrapeForm onScrape={handleScrape} loading={loading} status={status} error={error} />

        <PendingList
          offres={pending}
          onValidate={(ref) => { setPending(p => p.filter(o => o.reference !== ref)); fetchValidated(validatedDateFilter); }}
          onUpdate={(ref, data) => setPending(p => p.map(o => o.reference === ref ? { ...o, ...data } : o))}
          onDelete={(ref) => setPending(p => p.filter(o => o.reference !== ref))}
          onDateFilterChange={handlePendingDateFilter}
        />

        <ValidatedList
          tenders={validated}
          onRefresh={() => fetchValidated(validatedDateFilter)}
          onDateFilterChange={handleValidatedDateFilter}
        />
      </div>
    </div>
  );
};

export default Armp;