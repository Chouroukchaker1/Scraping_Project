# Backend Dockerfile - Node.js + Python
FROM python:3.11-slim

# Installer Node.js et Chromium pour Selenium
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-ara \
    chromium \
    chromium-driver \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances Python
COPY requirements.txt ./

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier les fichiers de dépendances Node.js
COPY package*.json ./

# Installer les dépendances Node.js
RUN npm ci --only=production

# Copier le code source
COPY . .

# Créer les répertoires nécessaires
RUN mkdir -p output excelpnud screenshots pdf_tuneps_extraction images logs

# Exposer le port principal
EXPOSE 5000

# Exposer les ports des scrapers Python
EXPOSE 5003 5005 5006 5007 5010 5011 5012 5013 5014 5015 5016 5017

# Variables d'environnement par défaut
ENV NODE_ENV=production
ENV PORT=5000
ENV DATABASE_URL=postgresql://tender_user:tender_password_2024@postgres:5432/tenders_db
ENV DB_HOST=postgres
ENV DB_PORT=5432
ENV DB_NAME=tenders_db
ENV DB_USER=tender_user
ENV DB_PASSWORD=tender_password_2024
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Démarrer le serveur Node.js (qui lancera les scrapers Python)
CMD ["node", "server.js"]
