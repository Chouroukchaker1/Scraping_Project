const axios = require('axios');

const API_BASE_URL = 'https://be.appeloffres.net/api';
const API_EMAIL = 'maryam.marmouch@tunipages.tn';
const API_PASSWORD = 'Marmouch2345!@';
const LOGIN_ENDPOINT = `${API_BASE_URL}/auth/login/`;

console.log('🔐 Test de connexion à l\'API AppelOffres');
console.log('📧 Email utilisé:', API_EMAIL);
console.log('🌐 Endpoint:', LOGIN_ENDPOINT);
console.log('');

axios.post(LOGIN_ENDPOINT, {
  email: API_EMAIL,
  password: API_PASSWORD
}, {
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  timeout: 30000
}).then(response => {
  if (response.status === 200 || response.status === 201) {
    console.log('✅ CONNEXION RÉUSSIE avec le compte de Maryam!');
    console.log('📧 Email confirmé:', API_EMAIL);
    console.log('🎫 Token reçu:', response.data.accessToken ? 'OUI (' + response.data.accessToken.substring(0, 20) + '...)' : 'NON');
    console.log('');
    console.log('✅ CONFIRMATION: Les envois TUNEPS se feront avec le compte de MARYAM MARMOUCH');
  } else {
    console.log('❌ Échec connexion, status:', response.status);
  }
  process.exit(0);
}).catch(error => {
  console.log('❌ Erreur de connexion:', error.message);
  if (error.response) {
    console.log('Status:', error.response.status);
    console.log('Données:', error.response.data);
  }
  process.exit(1);
});
