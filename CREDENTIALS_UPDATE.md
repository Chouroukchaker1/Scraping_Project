# 🔐 Mise à jour des identifiants API AppelOffres

## ✅ Modification effectuée

Les identifiants pour l'envoi des offres TUNEPS AO vers l'API AppelOffres ont été mis à jour.

### Anciens identifiants
- Email: `maryam.marmouch@tunipages.tn`
- Mot de passe: `Marmouch2345!@`

### Nouveaux identifiants
- Email: `mariem.bousalem@tunipages.tn`
- Mot de passe: `L96BhA6ODugl`

## 📁 Fichiers modifiés

1. **backend/scripts/tuneps_ao.py**
   - Lignes 68-69: Identifiants par défaut
   - Configuration pour lire les variables d'environnement

2. **backend/.env**
   - Variables `API_EMAIL` et `API_PASSWORD`
   - URL de l'API: `https://be.appeloffres.net/api`

3. **docker-compose.yml**
   - Variables d'environnement pour le conteneur backend
   - `API_EMAIL=mariem.bousalem@tunipages.tn`
   - `API_PASSWORD=L96BhA6ODugl`

## 🔄 Configuration utilisée

### En local (développement)
Le script utilise les valeurs par défaut définies dans `tuneps_ao.py`:
```python
EMAIL = os.getenv("API_EMAIL", "mariem.bousalem@tunipages.tn")
API_PASSWORD = os.getenv("API_PASSWORD", "L96BhA6ODugl")
```

### En Docker (production)
Les valeurs sont injectées via les variables d'environnement dans `docker-compose.yml`:
```yaml
environment:
  - API_EMAIL=mariem.bousalem@tunipages.tn
  - API_PASSWORD=L96BhA6ODugl
```

## 🎯 Endpoints de l'API

Toutes les offres validées depuis l'interface web seront envoyées vers:
- **API Base**: `https://be.appeloffres.net/api`
- **Login**: `https://be.appeloffres.net/api/auth/login/`
- **Tenders**: `https://be.appeloffres.net/api/tenders`

## 🧪 Vérification

### Vérifier les identifiants en local
```bash
cd backend
python -c "from scripts.tuneps_ao import EMAIL, API_PASSWORD; print(f'Email: {EMAIL}')"
```

### Vérifier les identifiants dans Docker
```bash
docker exec backend_tenders python3 -c "import os; print('EMAIL:', os.getenv('API_EMAIL'))"
```

### Tester la connexion à l'API
```bash
curl -X POST https://be.appeloffres.net/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"mariem.bousalem@tunipages.tn","password":"L96BhA6ODugl"}'
```

Réponse attendue:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "email": "mariem.bousalem@tunipages.tn",
    "id": 123
  }
}
```

## 🚀 Redémarrage

Si vous avez modifié les identifiants manuellement, redémarrez Docker:

```bash
# Arrêter les conteneurs
docker-compose down

# Reconstruire et redémarrer
docker-compose up --build -d

# Ou redémarrer seulement le backend
docker-compose restart backend
```

## 📊 Flux de validation

Quand une offre est validée dans l'interface:

1. **Frontend** → Appelle `/api/validate/:reference`
2. **Backend Flask** → Vérifie l'offre dans MongoDB
3. **Login API** → Authentification avec `mariem.bousalem@tunipages.tn`
4. **Upload** → Envoi de l'offre vers AppelOffres
5. **MongoDB** → Déplacement de `pending_tenders_marmouch_bd` vers `tenders_marmouch`

## 🔒 Sécurité

- ⚠️ Les identifiants sont stockés en clair dans `.env` et `docker-compose.yml`
- ⚠️ Ne jamais commit `.env` dans Git
- ✅ `.env` est dans `.gitignore`
- ✅ Les mots de passe ne sont jamais loggés en clair

## 📝 Notes

- Les identifiants sont utilisés uniquement pour l'envoi des offres validées
- Le scraping TUNEPS ne nécessite pas d'authentification
- Les offres en attente restent locales jusqu'à validation manuelle
- Source ID par défaut: `817` (TUNEPS Tunisie)
- Pays ID: `219` (Tunisie)
- Type d'avis: `2` (Appel d'offres)

Date de mise à jour: 24 décembre 2025
