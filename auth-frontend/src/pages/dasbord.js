// src/Dashboard.js - TUNEPS OFFRES
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import * as XLSX from 'xlsx';
import {
  Container, Typography, Box, TextField, Button,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
  CircularProgress, Pagination, Alert, Snackbar, Chip,
  AppBar, Toolbar, Dialog, DialogTitle, DialogContent, DialogActions,
  IconButton, Grid, Collapse, Card, CardContent, Divider,
  Tooltip, Badge
} from '@mui/material';
import ExitToAppIcon from '@mui/icons-material/ExitToApp';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import CloseIcon from '@mui/icons-material/Close';
import DeleteIcon from '@mui/icons-material/Delete';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import RefreshIcon from '@mui/icons-material/Refresh';
import SearchIcon from '@mui/icons-material/Search';
import DownloadIcon from '@mui/icons-material/Download';

// ⭐ IMPORTANT: Pointer vers Flask sur port 5003
const API_URL = 'http://localhost:5003';

const Dasbord = () => {
  const navigate = useNavigate();
  
  // États principaux
  const [dateDebut, setDateDebut] = useState(() => {
    const saved = localStorage.getItem('dateDebut');
    if (saved) return saved;
    // Par défaut: 6 mois avant aujourd'hui
    const sixMonthsAgo = new Date();
    sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
    return sixMonthsAgo.toISOString().split('T')[0];
  });
  
  const [dateFin, setDateFin] = useState(() => {
    const saved = localStorage.getItem('dateFin');
    return saved ? saved : new Date().toISOString().split('T')[0];
  });
  
  const [offres, setOffres] = useState([]);
  const [totalPages, setTotalPages] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [searchReference, setSearchReference] = useState('');
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [expandedRows, setExpandedRows] = useState(new Set());

  // États pour le modal d'édition
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingOffre, setEditingOffre] = useState(null);
  const [editedFields, setEditedFields] = useState({});

  const limit = 10;

  // Vérification authentification
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login');
    }
  }, [navigate]);

  // Sauvegarder les dates
  useEffect(() => {
    localStorage.setItem('dateDebut', dateDebut);
    localStorage.setItem('dateFin', dateFin);
  }, [dateDebut, dateFin]);

  // Charger les offres au montage
  useEffect(() => {
    console.log('🚀 Montage Dashboard TUNEPS OFFRES - Chargement initial...');
    loadOffres(1);
  }, []);

  // Fonction pour afficher les notifications
  const showSnackbar = (message, severity = 'success') => {
    console.log(`📢 [${severity}]:`, message);
    setSnackbar({ open: true, message, severity });
  };

  // Charger les offres paginées
  const loadOffres = async (page = 1) => {
    try {
      setLoading(true);
      console.log(`🔄 Chargement offres - Page ${page}...`);
      
      const res = await axios.get(`${API_URL}/api/pending?page=${page}&limit=${limit}`);
      console.log('📦 Réponse API pending:', res.data);
      
      if (res.data && res.data.success) {
        const pendingData = res.data.pending || {};
        const offresArray = Array.isArray(pendingData.offres) ? pendingData.offres : [];
        
        console.log(`✅ ${offresArray.length} offres chargées`);
        setOffres(offresArray);
        setTotalPages(pendingData.totalPages || 1);
        setCurrentPage(pendingData.page || 1);
        
        if (offresArray.length === 0) {
          showSnackbar('Aucune offre en attente. Lancez un scraping pour en récupérer.', 'info');
        }
      } else {
        console.warn('⚠️ Réponse API sans succès:', res.data);
        setOffres([]);
        showSnackbar('Aucune offre trouvée', 'warning');
      }
    } catch (err) {
      console.error('❌ Erreur chargement offres:', err);
      showSnackbar('Erreur chargement: ' + (err.response?.data?.message || err.message), 'error');
      setOffres([]);
    } finally {
      setLoading(false);
    }
  };

  // Fonction de logout
  const handleLogout = () => {
    localStorage.removeItem('token');
    showSnackbar('Déconnexion réussie', 'success');
    navigate('/login');
  };

  // Scraper les offres
  const handleScrape = async (completeMode = false) => {
    setLoading(true);
    console.log('🔍 Lancement scraping TUNEPS OFFRES...', { dateDebut, dateFin, completeMode });
    
    try {
      const res = await axios.post(`${API_URL}/api/scrape`, { 
        start_date: dateDebut, 
        end_date: dateFin,
        extraction_complete: completeMode
      });
      
      console.log('📦 Réponse scraping:', res.data);
      
      if (res.data && res.data.success) {
        showSnackbar(res.data.message || 'Scraping lancé en arrière-plan. Actualisez dans 30-60s.', 'success');
        
        // Attendre 5s puis recharger
        setTimeout(() => {
          loadOffres(1);
        }, 5000);
      } else {
        showSnackbar('Erreur lors du scraping', 'error');
      }
    } catch (err) {
      console.error('❌ Erreur scraping:', err);
      showSnackbar('Erreur scraping: ' + (err.response?.data?.message || err.message), 'error');
    } finally {
      setLoading(false);
    }
  };

  // Ouvrir le modal d'édition
  const handleEditOpen = (offre) => {
    setEditingOffre(offre);
    setEditedFields({
      description: offre.description || '',
      promoter: offre.promoter || '',
      publicationDate: offre.publicationDate || '',
      expirationDate: offre.expirationDate || '',
      ouverture_offres: offre.ouverture_offres || '',
      cautionnement_provisoire: offre.cautionnement_provisoire || '0',
      procedure: offre.procedure || 'N/A',
      type_marche: offre.type_marche || 'Public',
      url_source: offre.url_source || '',
      full_content: offre.full_content || ''
    });
    setEditModalOpen(true);
  };

  // Sauvegarder les modifications
  const handleSaveEdit = async () => {
    if (!editingOffre) return;

    try {
      const res = await axios.post(`${API_URL}/api/update/${editingOffre.reference}`, editedFields);
      
      if (res.data.success) {
        showSnackbar('Offre mise à jour avec succès');
        setEditModalOpen(false);
        await loadOffres(currentPage);
      } else {
        showSnackbar('Erreur lors de la mise à jour', 'error');
      }
    } catch (err) {
      console.error('Erreur update:', err);
      showSnackbar('Erreur: ' + (err.response?.data?.message || err.message), 'error');
    }
  };

  // Valider une offre
  const handleValidate = async (reference) => {
    console.log(`✅ Validation offre: ${reference}`);
    
    try {
      const res = await axios.post(`${API_URL}/api/validate/${reference}`);
      console.log('📦 Réponse validation:', res.data);
      
      if (res.data && res.data.success) {
        await loadOffres(currentPage);
        showSnackbar(res.data.message || 'Offre validée avec succès');
      } else {
        showSnackbar(res.data.message || 'Erreur de validation', 'error');
      }
    } catch (err) {
      console.error('❌ Erreur validation:', err);
      showSnackbar('Erreur: ' + (err.response?.data?.message || err.message), 'error');
    }
  };

  // Supprimer une offre
  const handleDelete = async (reference) => {
    if (!window.confirm(`Confirmer la suppression de l'offre ${reference}?`)) return;
    
    console.log(`🗑️ Suppression offre: ${reference}`);
    
    try {
      const res = await axios.delete(`${API_URL}/api/delete/${reference}`);
      console.log('📦 Réponse suppression:', res.data);
      
      if (res.data && res.data.success) {
        await loadOffres(currentPage);
        showSnackbar(res.data.message || 'Offre supprimée');
      } else {
        showSnackbar(res.data.message || 'Erreur de suppression', 'error');
      }
    } catch (err) {
      console.error('❌ Erreur suppression:', err);
      showSnackbar('Erreur: ' + (err.response?.data?.message || err.message), 'error');
    }
  };

  // Télécharger PDF
  const handleDownloadPdf = (filename) => {
    if (!filename) {
      showSnackbar('Aucun PDF disponible', 'warning');
      return;
    }
    console.log(`📄 Téléchargement PDF: ${filename}`);
    window.open(`${API_URL}/api/download_pdf/${filename}`, '_blank');
  };

  // Télécharger en XLS
  const handleDownloadXLS = () => {
    if (!Array.isArray(offres) || offres.length === 0) {
      showSnackbar('Aucune offre à exporter', 'warning');
      return;
    }
    
    console.log(`📊 Export XLS de ${offres.length} offres`);
    
    try {
      const exportData = offres.map(offre => {
        const lotsInfo = offre.lots?.map((lot, i) => 
          `Lot ${i+1}: ${lot.title || lot.objet || 'N/A'} | Caution: ${lot.deposit || lot['Cautionnement provisoire'] || '0'}`
        ).join(' | ') || '';

        return {
          'Référence': offre.reference || '',
          'Description': offre.description || '',
          'Promoteur': offre.promoter || '',
          'Source': offre.source || '',
          'Pays': offre.pays || '',
          'Date Publication': offre.publicationDate || '',
          'Date Début Soumissions': offre.startBiddingDate || '',
          'Date Expiration': offre.expirationDate || '',
          'Date Ouverture Plis': offre.ouverture_offres || '',
          'Durée Validité Offre': offre.offer_validity_duration || '',
          'Cautionnement Global': offre.cautionnement_provisoire || '0',
          'Nombre de Lots': offre.lots?.length || 0,
          'Lots Détails': lotsInfo,
          'Procédure': offre.procedure || '',
          'Type Marché': offre.type_marche || '',
          'URL Source': offre.url_source || '',
          'PDF': offre.cahier_charge_pdf_filename || offre.image_filename || '',
          'Région ID': offre.region_id || ''
        };
      });
      
      const ws = XLSX.utils.json_to_sheet(exportData);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, "Offres TUNEPS");
      XLSX.writeFile(wb, `tuneps_offres_${new Date().toISOString().split('T')[0]}.xlsx`);
      showSnackbar('Export XLS généré avec succès');
    } catch (err) {
      console.error('❌ Erreur export XLS:', err);
      showSnackbar('Erreur lors de l\'export XLS', 'error');
    }
  };

  // Changer de page
  const handlePageChange = (event, page) => {
    console.log(`📄 Changement de page: ${page}`);
    loadOffres(page);
  };

  // Toggle expansion d'une ligne pour voir les lots
  const toggleRowExpand = (reference) => {
    setExpandedRows(prev => {
      const newSet = new Set(prev);
      if (newSet.has(reference)) {
        newSet.delete(reference);
      } else {
        newSet.add(reference);
      }
      return newSet;
    });
  };

  // Filtrer les offres par référence
  const filteredOffres = offres.filter(offre => 
    offre.reference?.toLowerCase().includes(searchReference.toLowerCase())
  );

  // Fermer la snackbar
  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  // Fermer le modal
  const handleCloseModal = () => {
    setEditModalOpen(false);
    setEditingOffre(null);
    setEditedFields({});
  };

  // Mise à jour des champs édités
  const handleFieldChange = (field, value) => {
    setEditedFields(prev => ({ ...prev, [field]: value }));
  };

  console.log('🎨 Rendu Dashboard - Offres:', filteredOffres.length);

  return (
    <>
      <AppBar position="static" sx={{ backgroundColor: '#1976d2' }}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            📋 Dashboard TUNEPS - Appels d'Offres (/portail/offres)
          </Typography>
          <Button
            variant="contained"
            color="secondary"
            onClick={handleLogout}
            startIcon={<ExitToAppIcon />}
            sx={{ color: 'white' }}
          >
            Déconnexion
          </Button>
        </Toolbar>
      </AppBar>
      
      <Container maxWidth="xl" sx={{ mt: 2 }}>
        {/* Formulaire de scraping */}
        <Box sx={{ mb: 4, p: 3, border: '1px solid #e0e0e0', borderRadius: 2, backgroundColor: '#fafafa' }}>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: '#2e7d32' }}>
            🚀 Lancer un scraping TUNEPS OFFRES
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center', mt: 2 }}>
            <TextField
              type="date"
              label="Date début"
              value={dateDebut}
              onChange={(e) => setDateDebut(e.target.value)}
              sx={{ minWidth: 150 }}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              type="date"
              label="Date fin"
              value={dateFin}
              onChange={(e) => setDateFin(e.target.value)}
              sx={{ minWidth: 150 }}
              InputLabelProps={{ shrink: true }}
            />
            
            <Button
              variant="contained"
              onClick={() => handleScrape(false)}
              disabled={loading}
              startIcon={loading ? <CircularProgress size={20} /> : <SearchIcon />}
              sx={{ 
                minWidth: 180,
                backgroundColor: '#2e7d32',
                '&:hover': { backgroundColor: '#1b5e20' }
              }}
            >
              {loading ? 'En cours...' : '🔍 Scraper (Rapide)'}
            </Button>

            <Button
              variant="contained"
              onClick={() => handleScrape(true)}
              disabled={loading}
              startIcon={loading ? <CircularProgress size={20} /> : <SearchIcon />}
              sx={{ 
                minWidth: 180,
                backgroundColor: '#1565c0',
                '&:hover': { backgroundColor: '#0d47a1' }
              }}
            >
              {loading ? 'En cours...' : '🔎 Scraper (Complet)'}
            </Button>
            
            <Button
              variant="outlined"
              onClick={() => loadOffres(1)}
              disabled={loading}
              startIcon={<RefreshIcon />}
              color="primary"
            >
              🔄 Recharger
            </Button>
          </Box>

          <Typography variant="body2" color="textSecondary" sx={{ mt: 2 }}>
            ℹ️ Mode Rapide: Liste uniquement (rapide) | Mode Complet: Extraction détaillée avec lots + cautionnements (lent)
          </Typography>
        </Box>

        {/* Barre d'actions */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 'bold', color: '#1976d2' }}>
            📋 Offres en attente ({filteredOffres.length} / {offres.length})
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
            <TextField
              label="🔍 Filtrer par référence"
              value={searchReference}
              onChange={(e) => setSearchReference(e.target.value)}
              sx={{ minWidth: 200 }}
              size="small"
            />
            <Button
              variant="outlined"
              onClick={handleDownloadXLS}
              disabled={!Array.isArray(offres) || offres.length === 0}
              startIcon={<DownloadIcon />}
            >
              📊 Exporter XLS
            </Button>
          </Box>
        </Box>

        {/* Table des offres */}
        <TableContainer component={Paper} sx={{ mb: 3 }}>
          <Table sx={{ minWidth: 1400 }} aria-label="offres table">
            <TableHead>
              <TableRow sx={{ backgroundColor: '#1976d2' }}>
                <TableCell sx={{ color: 'white', fontWeight: 'bold', width: 50 }}></TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Référence</TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Description</TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Promoteur</TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Date Publication</TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Date Expiration</TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Date Ouverture Plis</TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Cautionnement</TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Lots</TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={10} align="center" sx={{ py: 6 }}>
                    <CircularProgress />
                    <Typography variant="body2" sx={{ mt: 2 }}>
                      Chargement des offres...
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : Array.isArray(filteredOffres) && filteredOffres.length > 0 ? (
                filteredOffres.map((offre) => {
                  const isExpanded = expandedRows.has(offre.reference);
                  const hasLots = Array.isArray(offre.lots) && offre.lots.length > 0;
                  
                  return (
                    <React.Fragment key={offre.reference}>
                      <TableRow 
                        sx={{ 
                          '&:hover': { backgroundColor: '#f5f5f5' },
                          backgroundColor: hasLots ? '#f0f8ff' : 'white'
                        }}
                      >
                        <TableCell>
                          {hasLots && (
                            <IconButton
                              size="small"
                              onClick={() => toggleRowExpand(offre.reference)}
                            >
                              {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                            </IconButton>
                          )}
                        </TableCell>
                        
                        <TableCell sx={{ fontWeight: 'bold', fontSize: '0.9rem' }}>
                          {offre.reference}
                          {hasLots && (
                            <Chip 
                              label={`${offre.lots.length} lot(s)`} 
                              size="small" 
                              color="primary" 
                              sx={{ ml: 1, fontSize: '0.7rem' }}
                            />
                          )}
                        </TableCell>
                        
                        <TableCell sx={{ maxWidth: 300, wordWrap: 'break-word', fontSize: '0.85rem' }}>
                          {offre.description}
                        </TableCell>
                        
                        <TableCell sx={{ fontSize: '0.85rem', maxWidth: 200 }}>
                          {offre.promoter}
                        </TableCell>
                        
                        <TableCell>
                          <Typography variant="body2" sx={{ fontSize: '0.85rem' }}>
                            {offre.publicationDate || 'N/A'}
                          </Typography>
                        </TableCell>
                        
                        <TableCell>
                          <Typography 
                            variant="body2" 
                            sx={{ 
                              fontSize: '0.85rem',
                              color: offre.expirationDate === 'N/A' ? 'error.main' : 'inherit'
                            }}
                          >
                            {offre.expirationDate}
                          </Typography>
                        </TableCell>

                        <TableCell>
                          <Tooltip title="Date et heure d'ouverture des plis">
                            <Typography 
                              variant="body2" 
                              sx={{ 
                                fontSize: '0.85rem',
                                color: offre.ouverture_offres === 'N/A' ? 'warning.main' : 'success.main',
                                fontWeight: 'bold'
                              }}
                            >
                              {offre.ouverture_offres || 'N/A'}
                            </Typography>
                          </Tooltip>
                        </TableCell>

                        <TableCell>
                          <Chip 
                            label={offre.cautionnement_provisoire || '0'} 
                            size="small" 
                            color={offre.cautionnement_provisoire && offre.cautionnement_provisoire !== '0' ? 'success' : 'default'}
                            sx={{ fontWeight: 'bold' }}
                          />
                        </TableCell>

                        <TableCell>
                          {hasLots ? (
                            <Badge badgeContent={offre.lots.length} color="primary">
                              <Chip 
                                label="Voir lots" 
                                size="small" 
                                color="info"
                                onClick={() => toggleRowExpand(offre.reference)}
                              />
                            </Badge>
                          ) : (
                            <Typography variant="body2" color="textSecondary" fontStyle="italic">
                              Aucun
                            </Typography>
                          )}
                        </TableCell>
                        
                        <TableCell sx={{ minWidth: 250 }}>
                          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                            <Tooltip title="Modifier">
                              <IconButton 
                                size="small" 
                                onClick={() => handleEditOpen(offre)} 
                                color="primary"
                              >
                                <EditIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                            
                            <Tooltip title="Valider et envoyer à l'API">
                              <Button 
                                size="small" 
                                onClick={() => handleValidate(offre.reference)} 
                                variant="contained" 
                                color="success"
                                startIcon={<CheckCircleIcon />}
                              >
                                Valider
                              </Button>
                            </Tooltip>
                            
                            <Tooltip title="Supprimer">
                              <IconButton 
                                size="small" 
                                onClick={() => handleDelete(offre.reference)} 
                                color="error"
                              >
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                            
                            {(offre.cahier_charge_pdf_filename || offre.image_filename) && (
                              <Tooltip title="Télécharger PDF">
                                <IconButton
                                  size="small"
                                  onClick={() => handleDownloadPdf(offre.cahier_charge_pdf_filename || offre.image_filename)}
                                  color="secondary"
                                >
                                  <PictureAsPdfIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            )}

                            {offre.url_source && (
                              <Tooltip title="Voir source TUNEPS">
                                <Button
                                  size="small"
                                  variant="outlined"
                                  color="info"
                                  onClick={() => window.open(offre.url_source, '_blank')}
                                >
                                  🔗
                                </Button>
                              </Tooltip>
                            )}
                          </Box>
                        </TableCell>
                      </TableRow>

                      {/* Ligne expandable pour afficher les lots */}
                      {hasLots && (
                        <TableRow>
                          <TableCell colSpan={10} sx={{ paddingBottom: 0, paddingTop: 0 }}>
                            <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                              <Box sx={{ margin: 2 }}>
                                <Typography variant="h6" gutterBottom component="div" sx={{ color: '#1976d2' }}>
                                  📦 Lots de l'offre {offre.reference}
                                </Typography>
                                <Table size="small" aria-label="lots">
                                  <TableHead>
                                    <TableRow sx={{ backgroundColor: '#e3f2fd' }}>
                                      <TableCell sx={{ fontWeight: 'bold' }}>N°</TableCell>
                                      <TableCell sx={{ fontWeight: 'bold' }}>Titre / Objet</TableCell>
                                      <TableCell sx={{ fontWeight: 'bold' }}>Cautionnement</TableCell>
                                      <TableCell sx={{ fontWeight: 'bold' }}>Montant Estimé</TableCell>
                                      <TableCell sx={{ fontWeight: 'bold' }}>Autres Infos</TableCell>
                                    </TableRow>
                                  </TableHead>
                                  <TableBody>
                                    {offre.lots.map((lot, index) => (
                                      <TableRow key={index}>
                                        <TableCell>{index + 1}</TableCell>
                                        <TableCell sx={{ maxWidth: 400 }}>
                                          {lot.title || lot.objet || lot.description || 'N/A'}
                                        </TableCell>
                                        <TableCell>
                                          <Chip 
                                            label={lot.deposit || lot['Cautionnement provisoire'] || '0'} 
                                            size="small" 
                                            color="success"
                                            sx={{ fontWeight: 'bold' }}
                                          />
                                        </TableCell>
                                        <TableCell>
                                          {lot.montant_estime || lot.Montant || 'N/A'}
                                        </TableCell>
                                        <TableCell>
                                          {Object.entries(lot)
                                            .filter(([key]) => !['title', 'objet', 'description', 'deposit', 'Cautionnement provisoire', 'montant_estime', 'Montant'].includes(key))
                                            .map(([key, value]) => (
                                              <Typography key={key} variant="caption" display="block">
                                                <strong>{key}:</strong> {value}
                                              </Typography>
                                            ))
                                          }
                                        </TableCell>
                                      </TableRow>
                                    ))}
                                  </TableBody>
                                </Table>
                              </Box>
                            </Collapse>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  );
                })
              ) : (
                <TableRow>
                  <TableCell colSpan={10} align="center" sx={{ py: 6 }}>
                    <Typography variant="h6" color="textSecondary" gutterBottom>
                      {Array.isArray(offres) && offres.length > 0 
                        ? '🔍 Aucune offre ne correspond au filtre' 
                        : '📭 Aucune offre en attente'
                      }
                    </Typography>
                    <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                      {Array.isArray(offres) && offres.length > 0 
                        ? 'Essayez un autre filtre'
                        : 'Utilisez le bouton "Scraper" pour récupérer des offres TUNEPS'
                      }
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Pagination */}
        {totalPages > 1 && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3, mb: 4 }}>
            <Pagination
              count={totalPages}
              page={currentPage}
              onChange={handlePageChange}
              color="primary"
              showFirstButton
              showLastButton
              size="large"
            />
          </Box>
        )}

        {/* Modal d'édition */}
        <Dialog open={editModalOpen} onClose={handleCloseModal} maxWidth="md" fullWidth>
          <DialogTitle>
            ✏️ Modifier l'offre: {editingOffre?.reference}
            <IconButton
              aria-label="close"
              onClick={handleCloseModal}
              sx={{
                position: 'absolute',
                right: 8,
                top: 8,
                color: (theme) => theme.palette.grey[500],
              }}
            >
              <CloseIcon />
            </IconButton>
          </DialogTitle>
          <DialogContent>
            {editingOffre && (
              <Grid container spacing={2} sx={{ mt: 1 }}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Description"
                    value={editedFields.description || ''}
                    onChange={(e) => handleFieldChange('description', e.target.value)}
                    multiline
                    rows={3}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Promoteur"
                    value={editedFields.promoter || ''}
                    onChange={(e) => handleFieldChange('promoter', e.target.value)}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Cautionnement Provisoire"
                    value={editedFields.cautionnement_provisoire || ''}
                    onChange={(e) => handleFieldChange('cautionnement_provisoire', e.target.value)}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Date Publication"
                    type="date"
                    value={editedFields.publicationDate ? editedFields.publicationDate.split(' ')[0] : ''}
                    onChange={(e) => handleFieldChange('publicationDate', e.target.value)}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Date Expiration"
                    type="date"
                    value={editedFields.expirationDate ? editedFields.expirationDate.split(' ')[0] : ''}
                    onChange={(e) => handleFieldChange('expirationDate', e.target.value)}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Date Ouverture Plis"
                    value={editedFields.ouverture_offres || ''}
                    onChange={(e) => handleFieldChange('ouverture_offres', e.target.value)}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Procédure"
                    value={editedFields.procedure || ''}
                    onChange={(e) => handleFieldChange('procedure', e.target.value)}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Type Marché"
                    value={editedFields.type_marche || ''}
                    onChange={(e) => handleFieldChange('type_marche', e.target.value)}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="URL Source"
                    value={editedFields.url_source || ''}
                    onChange={(e) => handleFieldChange('url_source', e.target.value)}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Contenu Complet (aperçu)"
                    value={editedFields.full_content || ''}
                    onChange={(e) => handleFieldChange('full_content', e.target.value)}
                    multiline
                    rows={4}
                  />
                </Grid>

                {/* Affichage des lots si présents */}
                {editingOffre.lots && editingOffre.lots.length > 0 && (
                  <Grid item xs={12}>
                    <Divider sx={{ my: 2 }} />
                    <Typography variant="h6" gutterBottom>
                      📦 Lots ({editingOffre.lots.length})
                    </Typography>
                    {editingOffre.lots.map((lot, index) => (
                      <Card key={index} sx={{ mb: 2, backgroundColor: '#f5f5f5' }}>
                        <CardContent>
                          <Typography variant="subtitle2" color="primary">
                            Lot {index + 1}
                          </Typography>
                          <Typography variant="body2">
                            <strong>Titre:</strong> {lot.title || lot.objet || lot.description || 'N/A'}
                          </Typography>
                          <Typography variant="body2">
                            <strong>Cautionnement:</strong> {lot.deposit || lot['Cautionnement provisoire'] || '0'}
                          </Typography>
                          {lot.montant_estime && (
                            <Typography variant="body2">
                              <strong>Montant estimé:</strong> {lot.montant_estime}
                            </Typography>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </Grid>
                )}
              </Grid>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseModal} color="primary">
              Annuler
            </Button>
            <Button onClick={handleSaveEdit} variant="contained" startIcon={<SaveIcon />} color="primary">
              Sauvegarder
            </Button>
            <Button 
              onClick={() => { 
                handleSaveEdit(); 
                handleValidate(editingOffre?.reference); 
                handleCloseModal(); 
              }} 
              variant="contained" 
              color="success"
              startIcon={<CheckCircleIcon />}
            >
              Sauvegarder & Valider
            </Button>
          </DialogActions>
        </Dialog>

        {/* Snackbar pour les notifications */}
        <Snackbar
          open={snackbar.open}
          autoHideDuration={6000}
          onClose={handleCloseSnackbar}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
        >
          <Alert 
            onClose={handleCloseSnackbar} 
            severity={snackbar.severity} 
            sx={{ width: '100%' }}
          >
            {snackbar.message}
          </Alert>
        </Snackbar>
      </Container>
    </>
  );
};

export default Dasbord;