// src/Dashboard.js
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import * as XLSX from 'xlsx';
import {
  Container, Typography, Box, TextField, FormControlLabel, Checkbox, Button,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
  Select, MenuItem, CircularProgress, Pagination, Alert, Snackbar, Chip,
  AppBar, Toolbar, Dialog, DialogTitle, DialogContent, DialogActions,
  IconButton, Grid, InputLabel, FormControl
} from '@mui/material';
import ExitToAppIcon from '@mui/icons-material/ExitToApp';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import CloseIcon from '@mui/icons-material/Close';

// ✅ API pointe vers le backend Flask sur port 5003
const API_URL = 'http://localhost:5003';

const Dashboard = () => {
  const navigate = useNavigate();
  
  const [dateDebut, setDateDebut] = useState(() => {
    const saved = localStorage.getItem('dateDebut');
    if (saved) return saved;
    const today = new Date();
    return today.toISOString().split('T')[0];
  });
  
  const [dateFin, setDateFin] = useState(() => {
    const saved = localStorage.getItem('dateFin');
    return saved ? saved : new Date().toISOString().split('T')[0];
  });
  
  const [categories, setCategories] = useState(() => {
    const saved = localStorage.getItem('categories');
    return saved ? JSON.parse(saved) : ['all'];
  });
  
  const [offres, setOffres] = useState([]);
  const [totalPages, setTotalPages] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);
  const [secteurs, setSecteurs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchReference, setSearchReference] = useState('');
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingOffre, setEditingOffre] = useState(null);
  const [editedFields, setEditedFields] = useState({});

  const limit = 10;

  // ⚠️ SUPPRIMÉ : la vérification du token qui redirigeait vers /login
  // useEffect(() => {
  //   const token = localStorage.getItem('token');
  //   if (!token) {
  //     navigate('/login');
  //   }
  // }, [navigate]);

  useEffect(() => {
    localStorage.setItem('dateDebut', dateDebut);
    localStorage.setItem('dateFin', dateFin);
    localStorage.setItem('categories', JSON.stringify(categories));
  }, [dateDebut, dateFin, categories]);

  useEffect(() => {
    const loadSecteurs = async () => {
      try {
        console.log('🔄 Chargement des secteurs depuis:', `${API_URL}/api/secteurs`);
        const res = await axios.get(`${API_URL}/api/secteurs`);
        const secteursArray = res.data?.results || [];
        console.log('✅ Secteurs chargés:', secteursArray.length);
        setSecteurs(secteursArray);
      } catch (err) {
        console.error('❌ Erreur chargement secteurs:', err);
        showSnackbar('Erreur lors du chargement des secteurs', 'error');
        setSecteurs([]);
      }
    };
    loadSecteurs();
  }, []);

  const loadOffres = async (page = 1) => {
    try {
      setLoading(true);
      console.log('🔄 Chargement des offres - page', page);
      const res = await axios.get(`${API_URL}/api/pending?page=${page}&limit=${limit}`);
      
      if (res.data && res.data.success) {
        const pendingData = res.data.pending || {};
        const offresArray = Array.isArray(pendingData.offres) ? pendingData.offres : [];
        
        console.log('✅ Offres chargées:', offresArray.length);
        setOffres(offresArray);
        setTotalPages(pendingData.totalPages || 1);
        setCurrentPage(pendingData.page || 1);
        
        if (offresArray.length === 0) {
          showSnackbar('Aucune offre en attente. Lancez un scraping.', 'info');
        }
      } else {
        setOffres([]);
        showSnackbar('Aucune offre trouvée', 'warning');
      }
    } catch (err) {
      console.error('❌ Erreur chargement offres:', err);
      showSnackbar('Erreur: ' + (err.response?.data?.message || err.message), 'error');
      setOffres([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    console.log('🚀 Chargement initial des offres...');
    loadOffres(1);
  }, []);

  const showSnackbar = (message, severity = 'success') => {
    setSnackbar({ open: true, message, severity });
  };

  // Le bouton de déconnexion reste, mais il ne fait plus rien d'obligatoire
  const handleLogout = () => {
    localStorage.removeItem('token');
    showSnackbar('Déconnexion effectuée (mode sans authentification)');
    // Pas de redirection forcée vers /login
    // navigate('/login');  ← Commenté ou supprimé si tu veux rester sur le dashboard
  };

  const handleScrape = async () => {
    if (!dateDebut || !dateFin) {
      showSnackbar('Veuillez sélectionner des dates', 'warning');
      return;
    }

    setLoading(true);
    console.log('🔍 Lancement scraping:', { dateDebut, dateFin, categories });
    
    try {
      const res = await axios.post(`${API_URL}/api/scrape`, { 
        date_debut: dateDebut, 
        date_fin: dateFin, 
        categories 
      });
      
      console.log('📦 Résultat scraping:', res.data);
      
      if (res.data && res.data.success) {
        const offresData = res.data.offres || {};
        const offresArray = Array.isArray(offresData.offres) ? offresData.offres : [];
        const stats = res.data.stats || {};
        
        setOffres(offresArray);
        setTotalPages(offresData.totalPages || 1);
        setCurrentPage(offresData.page || 1);
        
        showSnackbar(
          `✅ Scraping terminé ! ${offresArray.length} offres trouvées (${stats.accepted_with_keywords || 0} acceptées, ${stats.rejected_no_keywords || 0} rejetées)`,
          'success'
        );
      } else {
        setOffres([]);
        showSnackbar('Aucune offre trouvée', 'warning');
      }
    } catch (err) {
      console.error('❌ Erreur scraping:', err);
      showSnackbar('Erreur scraping: ' + (err.response?.data?.message || err.message), 'error');
      setOffres([]);
    } finally {
      setLoading(false);
    }
  };

  const handleEditOpen = (offre) => {
    setEditingOffre(offre);
    setEditedFields({
      description: offre.description || '',
      promoter: offre.promoter || '',
      publicationDate: offre.publicationDate || '',
      expirationDate: offre.expirationDate || '',
      secteur_activite_id: offre.secteur_activite_id || '',
      avis: offre.avis || '1',
      procedure: offre.procedure || 'N/A',
      type_marche: offre.type_marche || 'Public',
      url_source: offre.url_source || '',
      full_content: offre.full_content || ''
    });
    setEditModalOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!editingOffre) return;

    try {
      const res = await axios.post(`${API_URL}/api/update/${editingOffre.reference}`, editedFields);
      
      if (res.data.success) {
        showSnackbar('Offre mise à jour');
        setEditModalOpen(false);
        await loadOffres(currentPage);
      } else {
        showSnackbar('Erreur mise à jour', 'error');
      }
    } catch (err) {
      console.error('Erreur update:', err);
      showSnackbar('Erreur: ' + (err.response?.data?.message || err.message), 'error');
    }
  };

  const handleValidate = async (reference) => {
    try {
      console.log('✅ Validation:', reference);
      const res = await axios.post(`${API_URL}/api/validate/${reference}`);
      
      if (res.data && res.data.success) {
        await loadOffres(currentPage);
        showSnackbar(res.data.message || 'Offre validée');
      } else {
        showSnackbar(res.data.message || 'Erreur validation', 'error');
      }
    } catch (err) {
      console.error('❌ Erreur validation:', err);
      showSnackbar('Erreur: ' + (err.response?.data?.message || err.message), 'error');
    }
  };

  const handleDelete = async (reference) => {
    if (!window.confirm('Confirmer la suppression?')) return;

    try {
      const res = await axios.delete(`${API_URL}/api/delete/${reference}`);

      if (res.data && res.data.success) {
        await loadOffres(currentPage);
        showSnackbar('Offre supprimée');
      } else {
        showSnackbar('Erreur suppression', 'error');
      }
    } catch (err) {
      console.error('❌ Erreur suppression:', err);
      showSnackbar('Erreur: ' + (err.response?.data?.message || err.message), 'error');
    }
  };

  const handleDeleteAll = async () => {
    if (!window.confirm('⚠️ ATTENTION : Voulez-vous vraiment supprimer TOUTES les offres pending?\n\nCette action est irréversible!')) return;

    setLoading(true);
    try {
      const res = await axios.delete(`${API_URL}/api/delete_all`);

      if (res.data && res.data.success) {
        const count = res.data.count || 0;
        setOffres([]);
        setTotalPages(1);
        setCurrentPage(1);
        showSnackbar(`✅ ${count} offres supprimées avec succès`, 'success');
      } else {
        showSnackbar('Erreur suppression', 'error');
      }
    } catch (err) {
      console.error('❌ Erreur suppression toutes offres:', err);
      showSnackbar('Erreur: ' + (err.response?.data?.message || err.message), 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = (filename) => {
    if (!filename) {
      showSnackbar('Aucun PDF disponible', 'warning');
      return;
    }
    window.open(`${API_URL}/api/download_pdf/${filename}`, '_blank');
  };

  const handleDownloadXLS = () => {
    if (!Array.isArray(offres) || offres.length === 0) {
      showSnackbar('Aucune offre à exporter', 'warning');
      return;
    }
    
    try {
      const exportData = offres.map(offre => ({
        'Référence': offre.reference || '',
        'Description': offre.description || '',
        'Secteur': offre.secteur_activite || '',
        'Secteur ID': offre.secteur_activite_id || '',
        'Activités IDs': offre.activities_ids?.join(', ') || '',
        'Promoteur': offre.promoter || '',
        'Source': offre.source || '',
        'Pays': offre.pays || '',
        'Date Publication': offre.publicationDate || '',
        'Date Expiration': offre.expirationDate || '',
        'URL Source': offre.url_source || '',
        'Mots-clés': Array.isArray(offre.mots_cles_detectes) ? offre.mots_cles_detectes.join(', ') : ''
      }));
      
      const ws = XLSX.utils.json_to_sheet(exportData);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, "Offres BOAMP");
      XLSX.writeFile(wb, `offres_boamp_${new Date().toISOString().split('T')[0]}.xlsx`);
      showSnackbar('Export XLS réussi');
    } catch (err) {
      console.error('❌ Erreur export:', err);
      showSnackbar('Erreur export XLS', 'error');
    }
  };

  const handlePageChange = (event, page) => {
    loadOffres(page);
  };

  const toggleCategory = (cat) => {
    setCategories(prev => {
      const newCategories = prev.includes(cat) 
        ? prev.filter(c => c !== cat) 
        : [...prev, cat];
      localStorage.setItem('categories', JSON.stringify(newCategories));
      return newCategories;
    });
  };

  const selectAllCategories = () => {
    setCategories(['all']);
    localStorage.setItem('categories', JSON.stringify(['all']));
  };

  const filteredOffres = offres.filter(offre => 
    offre.reference?.toLowerCase().includes(searchReference.toLowerCase())
  );

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  const handleCloseModal = () => {
    setEditModalOpen(false);
    setEditingOffre(null);
    setEditedFields({});
  };

  const handleFieldChange = (field, value) => {
    setEditedFields(prev => ({ ...prev, [field]: value }));
  };

  return (
    <>
      <AppBar position="static" sx={{ backgroundColor: '#1976d2' }}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            📊 Scraper BOAMP - 71 Mots-clés (Frontend React)
          </Typography>
          <Chip 
            label={`Backend: ${API_URL}`} 
            color="success" 
            variant="outlined" 
            sx={{ mr: 2, color: 'white', borderColor: 'white' }}
          />
          <Button
            variant="contained"
            color="secondary"
            onClick={handleLogout}
            startIcon={<ExitToAppIcon />}
          >
            Déconnexion
          </Button>
        </Toolbar>
      </AppBar>
      
      <Container maxWidth="xl" sx={{ mt: 2 }}>
        {/* Le reste du JSX est IDENTIQUE à l'original */}
        {/* Formulaire de scraping */}
        <Box sx={{ mb: 4, p: 3, border: '1px solid #e0e0e0', borderRadius: 2, backgroundColor: '#fafafa' }}>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: '#2e7d32' }}>
            🚀 Lancer un scraping BOAMP
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
              variant={categories.includes('all') ? 'contained' : 'outlined'}
              onClick={selectAllCategories}
              color="primary"
              size="small"
            >
              ✅ Tous secteurs
            </Button>
            
            <Button
              variant="contained"
              onClick={handleScrape}
              disabled={loading}
              startIcon={loading ? <CircularProgress size={20} color="inherit" /> : null}
              sx={{ 
                minWidth: 200,
                backgroundColor: '#2e7d32',
                '&:hover': { backgroundColor: '#1b5e20' }
              }}
            >
              {loading ? 'Scraping...' : '🔍 Scraper BOAMP'}
            </Button>
            
            <Button
              variant="outlined"
              onClick={() => loadOffres(1)}
              disabled={loading}
              color="primary"
            >
              🔄 Recharger
            </Button>
          </Box>
          
          <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
            {secteurs.length > 0 ? `✅ ${secteurs.length} secteurs chargés` : '⏳ Chargement secteurs...'}
          </Typography>
        </Box>

        {/* Liste des offres */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 'bold', color: '#1976d2' }}>
            📋 Offres en attente ({filteredOffres.length} / {offres.length})
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
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
              disabled={offres.length === 0}
            >
              📊 Export XLS
            </Button>
            <Button
              variant="outlined"
              color="error"
              onClick={handleDeleteAll}
              disabled={offres.length === 0 || loading}
              sx={{ fontWeight: 'bold' }}
            >
              🗑️ Supprimer Tous
            </Button>
          </Box>
        </Box>

        <TableContainer component={Paper} sx={{ mb: 3 }}>
          <Table sx={{ minWidth: 1200 }}>
            <TableHead>
              <TableRow sx={{ backgroundColor: '#1976d2' }}>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Référence</TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Description</TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Mots-clés</TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Secteur</TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Promoteur</TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Date Pub</TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Date Exp</TableCell>
                <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 6 }}>
                    <CircularProgress />
                    <Typography variant="body2" sx={{ mt: 2 }}>Chargement...</Typography>
                  </TableCell>
                </TableRow>
              ) : filteredOffres.length > 0 ? (
                filteredOffres.map((offre) => (
                  <TableRow 
                    key={offre.reference}
                    sx={{ '&:hover': { backgroundColor: '#f5f5f5' } }}
                  >
                    <TableCell sx={{ fontWeight: 'bold', fontSize: '0.9rem' }}>
                      {offre.reference}
                    </TableCell>
                    <TableCell sx={{ maxWidth: 250, wordWrap: 'break-word', fontSize: '0.85rem' }}>
                      {offre.description}
                    </TableCell>
                    <TableCell sx={{ maxWidth: 150 }}>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {Array.isArray(offre.mots_cles_detectes) && offre.mots_cles_detectes.length > 0 ? (
                          offre.mots_cles_detectes.slice(0, 2).map((mot, index) => (
                            <Chip
                              key={index}
                              label={mot}
                              size="small"
                              color="primary"
                              variant="outlined"
                              sx={{ fontSize: '0.7rem' }}
                            />
                          ))
                        ) : (
                          <Typography variant="body2" color="textSecondary">-</Typography>
                        )}
                      </Box>
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.85rem' }}>
                      {offre.secteur_activite || 'Non classé'}
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.85rem' }}>
                      {offre.promoter}
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.85rem' }}>
                      {offre.publicationDate}
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.85rem' }}>
                      {offre.expirationDate}
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                        <IconButton 
                          size="small" 
                          onClick={() => handleEditOpen(offre)}
                          color="primary"
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                        
                        <Button 
                          size="small" 
                          onClick={() => handleValidate(offre.reference)}
                          variant="contained" 
                          color="success"
                        >
                          ✅
                        </Button>
                        
                        <Button 
                          size="small" 
                          onClick={() => handleDelete(offre.reference)}
                          variant="outlined" 
                          color="error"
                        >
                          🗑️
                        </Button>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 6 }}>
                    <Typography variant="h6" color="textSecondary">
                      {offres.length > 0 ? '🔍 Aucune offre filtrée' : '📭 Aucune offre'}
                    </Typography>
                    <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                      {offres.length > 0 ? 'Modifiez le filtre' : 'Lancez un scraping'}
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {totalPages > 1 && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3, mb: 4 }}>
            <Pagination
              count={totalPages}
              page={currentPage}
              onChange={handlePageChange}
              color="primary"
              showFirstButton
              showLastButton
            />
          </Box>
        )}

        {/* Modal d'édition */}
        <Dialog open={editModalOpen} onClose={handleCloseModal} maxWidth="md" fullWidth>
          <DialogTitle>
            ✏️ Modifier: {editingOffre?.reference}
            <IconButton
              onClick={handleCloseModal}
              sx={{ position: 'absolute', right: 8, top: 8 }}
            >
              <CloseIcon />
            </IconButton>
          </DialogTitle>
          <DialogContent>
            {editingOffre && (
              <Grid container spacing={2} sx={{ mt: 1 }}>
                <Grid item xs={12} md={6}>
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
                  <FormControl fullWidth>
                    <InputLabel>Secteur</InputLabel>
                    <Select
                      value={editedFields.secteur_activite_id || ''}
                      label="Secteur"
                      onChange={(e) => handleFieldChange('secteur_activite_id', e.target.value)}
                    >
                      <MenuItem value=""><em>Sélectionner</em></MenuItem>
                      {secteurs.map((s) => (
                        <MenuItem key={s.id} value={s.id}>{s.name}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseModal}>Annuler</Button>
            <Button onClick={handleSaveEdit} variant="contained" startIcon={<SaveIcon />}>
              Sauvegarder
            </Button>
          </DialogActions>
        </Dialog>

        <Snackbar
          open={snackbar.open}
          autoHideDuration={6000}
          onClose={handleCloseSnackbar}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
        >
          <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} sx={{ width: '100%' }}>
            {snackbar.message}
          </Alert>
        </Snackbar>
      </Container>
    </>
  );
};

export default Dashboard;