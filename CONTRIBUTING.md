# 🤝 Guide de contribution

Merci de votre intérêt pour contribuer à la Plateforme d'Extraction d'Appels d'Offres !

## Code de conduite

En participant à ce projet, vous acceptez de respecter notre code de conduite. Soyez respectueux, inclusif et constructif.

## Comment contribuer

### 🐛 Signaler un bug

1. Vérifiez que le bug n'a pas déjà été signalé dans les [Issues](https://github.com/votre-repo/issues)
2. Créez une nouvelle issue avec le template "Bug Report"
3. Incluez:
   - Description claire du problème
   - Étapes pour reproduire
   - Comportement attendu vs actuel
   - Captures d'écran si pertinent
   - Version du système/navigateur
   - Logs pertinents

### ✨ Proposer une fonctionnalité

1. Créez une issue avec le template "Feature Request"
2. Décrivez:
   - Le problème que cela résout
   - La solution proposée
   - Les alternatives envisagées
   - Impact sur l'existant

### 🔧 Soumettre une Pull Request

#### 1. Fork et clone

```bash
# Fork le repo sur GitHub puis:
git clone https://github.com/votre-username/extraction-automatique.git
cd extraction-automatique
git remote add upstream https://github.com/repo-original/extraction-automatique.git
```

#### 2. Créer une branche

```bash
git checkout -b feature/ma-fonctionnalite
# ou
git checkout -b fix/mon-correctif
```

**Convention de nommage:**
- `feature/nom` - Nouvelle fonctionnalité
- `fix/nom` - Correction de bug
- `docs/nom` - Documentation
- `refactor/nom` - Refactoring
- `test/nom` - Tests
- `chore/nom` - Tâches diverses

#### 3. Développer

Suivez les standards de code (voir ci-dessous)

#### 4. Tester

```bash
# Backend
cd backend
npm test

# Frontend
cd auth-frontend
npm test

# Lint
npm run lint
```

#### 5. Commit

```bash
git add .
git commit -m "feat: ajouter export PDF pour PNUD"
```

**Convention de commit ([Conventional Commits](https://www.conventionalcommits.org/)):**

```
<type>(<scope>): <description>

[corps optionnel]

[footer optionnel]
```

**Types:**
- `feat`: Nouvelle fonctionnalité
- `fix`: Correction de bug
- `docs`: Documentation
- `style`: Formatage (pas de changement de code)
- `refactor`: Refactoring
- `test`: Ajout/modification de tests
- `chore`: Tâches de maintenance

**Exemples:**
```
feat(pnud): ajouter filtre par pays
fix(auth): corriger expiration token JWT
docs(readme): mettre à jour installation Docker
refactor(scrapers): extraire logique commune
test(api): ajouter tests endpoints auth
```

#### 6. Push et PR

```bash
git push origin feature/ma-fonctionnalite
```

Puis créez une Pull Request sur GitHub avec:
- Titre clair
- Description des changements
- Référence à l'issue (#123)
- Screenshots si UI
- Checklist complétée

## 📋 Checklist Pull Request

- [ ] Code suit les standards du projet
- [ ] Tests ajoutés/mis à jour
- [ ] Documentation mise à jour
- [ ] Pas de conflit avec main
- [ ] Commits suivent Conventional Commits
- [ ] Code lint sans erreur
- [ ] Testé localement

## 🎨 Standards de code

### JavaScript/Node.js

```javascript
// Utilisez des noms descriptifs
const getUserById = async (userId) => {
  // Code...
}

// Préférez const/let à var
const API_URL = 'http://localhost:5000';
let counter = 0;

// Async/await plutôt que callbacks
async function fetchData() {
  try {
    const response = await axios.get(API_URL);
    return response.data;
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
}

// Commentaires pour la logique complexe
// Calcul du hash SHA-256 pour validation
const hash = crypto.createHash('sha256').update(data).digest('hex');
```

### Python

```python
# PEP 8: snake_case pour fonctions/variables
def fetch_tenders_from_api(start_date, end_date):
    """
    Récupère les offres depuis l'API.

    Args:
        start_date (str): Date de début (YYYY-MM-DD)
        end_date (str): Date de fin (YYYY-MM-DD)

    Returns:
        list: Liste des offres
    """
    # Code...
    pass

# Type hints
from typing import List, Dict, Optional

def process_tender(tender: Dict) -> Optional[str]:
    if not tender:
        return None
    return tender.get('reference')

# Classes avec docstrings
class TenderScraper:
    """Scraper générique pour les appels d'offres."""

    def __init__(self, base_url: str):
        """
        Initialise le scraper.

        Args:
            base_url (str): URL de base du site
        """
        self.base_url = base_url
```

### React

```javascript
// Composants fonctionnels avec hooks
import React, { useState, useEffect } from 'react';

const TenderList = ({ sourceId }) => {
  const [tenders, setTenders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTenders();
  }, [sourceId]);

  const fetchTenders = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/tenders?source=${sourceId}`);
      setTenders(response.data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <Spinner />;

  return (
    <div className="tender-list">
      {tenders.map(tender => (
        <TenderCard key={tender.id} tender={tender} />
      ))}
    </div>
  );
};

export default TenderList;
```

### CSS

```css
/* BEM naming convention */
.tender-card {
  padding: 1rem;
  border-radius: 8px;
}

.tender-card__title {
  font-size: 1.5rem;
  font-weight: bold;
}

.tender-card__title--highlighted {
  color: #0066cc;
}

/* Variables CSS */
:root {
  --primary-color: #0066cc;
  --secondary-color: #6c757d;
  --border-radius: 8px;
}

.button {
  background-color: var(--primary-color);
  border-radius: var(--border-radius);
}
```

## 🧪 Tests

### Tests backend (Jest)

```javascript
// backend/tests/auth.test.js
describe('Auth Controller', () => {
  describe('POST /api/auth/login', () => {
    it('should return token for valid credentials', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'test@example.com',
          password: 'password123'
        });

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('token');
    });

    it('should return 401 for invalid credentials', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'test@example.com',
          password: 'wrongpassword'
        });

      expect(response.status).toBe(401);
    });
  });
});
```

### Tests frontend (Jest + React Testing Library)

```javascript
// auth-frontend/src/components/__tests__/Login.test.js
import { render, screen, fireEvent } from '@testing-library/react';
import Login from '../Login';

describe('Login Component', () => {
  it('should render login form', () => {
    render(<Login />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it('should call onSubmit with form data', () => {
    const mockSubmit = jest.fn();
    render(<Login onSubmit={mockSubmit} />);

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'test@example.com' }
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'password123' }
    });
    fireEvent.click(screen.getByRole('button', { name: /login/i }));

    expect(mockSubmit).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: 'password123'
    });
  });
});
```

## 📚 Documentation

- Documentez les nouvelles fonctionnalités dans README.md
- Ajoutez des docstrings pour les fonctions Python
- Commentez la logique complexe
- Mettez à jour API.md pour les nouveaux endpoints
- Ajoutez des exemples d'utilisation

## 🔍 Review process

1. **Automated checks**: Les tests et linting doivent passer
2. **Code review**: Au moins 1 approbation requise
3. **Testing**: Testez manuellement les changements
4. **Documentation**: Vérifiez que la doc est à jour
5. **Merge**: Squash and merge dans main

## 🎯 Priorités actuelles

Consultez le [Project Board](https://github.com/votre-repo/projects) pour voir:
- 🔴 Bugs critiques
- 🟡 Fonctionnalités prioritaires
- 🟢 Améliorations

## 💡 Idées de contributions

### Facile (bon pour débuter)
- Corriger des typos dans la documentation
- Ajouter des traductions
- Améliorer les messages d'erreur
- Ajouter des tests unitaires

### Moyen
- Ajouter un nouveau scraper
- Améliorer l'UI d'une page
- Optimiser les performances
- Ajouter des filtres avancés

### Avancé
- Implémenter le scraping distribué
- Ajouter le support multi-langue
- Créer un système de notifications
- Ajouter l'authentification OAuth

## 📞 Questions

- Discord: [Lien Discord]
- Email: dev@example.com
- Issues: Pour les questions techniques

## 🙏 Merci

Votre contribution est précieuse ! Même une petite amélioration fait une différence.

---

**Happy Coding! 💻**
