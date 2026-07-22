# Déploiement sur VPS Linux (Ubuntu / Debian)

Deux méthodes : **Docker** (recommandée, la plus simple) ou **installation native** (systemd).

---

## Méthode A — Docker (recommandée)

```bash
# 1. Cloner le dépôt
git clone https://github.com/<votre-compte>/cordiste-prospection-ai.git
cd cordiste-prospection-ai

# 2. Créer le fichier .env à partir de l'exemple
cp .env.example .env
nano .env            # renseignez SMTP_PASSWORD (mot de passe de la boîte LWS)

# 3. Démarrer
docker compose up -d --build

# 4. Vérifier
docker compose logs -f
```

Tableau de bord accessible sur `http://IP_DU_VPS:8000`.
La base SQLite est persistée dans `./data` (jamais réinitialisée).

Mise à jour ultérieure :

```bash
git pull && docker compose up -d --build
```

---

## Méthode B — Installation native (systemd)

```bash
# 1. Dépendances système
sudo apt update && sudo apt install -y python3-venv python3-pip git

# 2. Code + utilisateur dédié
sudo useradd -r -m -d /opt/cordiste-prospection-ai cordiste
sudo -u cordiste git clone https://github.com/<votre-compte>/cordiste-prospection-ai.git /opt/cordiste-prospection-ai
cd /opt/cordiste-prospection-ai

# 3. Environnement virtuel + dépendances
sudo -u cordiste python3 -m venv .venv
sudo -u cordiste .venv/bin/pip install -r requirements.txt

# 4. Configuration
sudo -u cordiste cp .env.example .env
sudo -u cordiste nano .env      # renseignez SMTP_PASSWORD

# 5a. Service web + scheduler interne (ENABLE_SCHEDULER=true)
sudo cp deploy/cordiste-web.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now cordiste-web

# 5b. (Optionnel) recherche pilotée par timer systemd au lieu du scheduler interne
#     -> mettez ENABLE_SCHEDULER=false dans .env
sudo cp deploy/cordiste-prospection.service /etc/systemd/system/
sudo cp deploy/cordiste-prospection.timer   /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now cordiste-prospection.timer
```

---

## Reverse proxy HTTPS (recommandé en production)

Exemple Nginx :

```nginx
server {
    server_name prospection.cordiste-ile-de-france.fr;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
    }
}
```

Puis `sudo certbot --nginx` pour le certificat Let's Encrypt.
Pensez à protéger l'accès (mot de passe HTTP basic ou VPN) : le tableau de bord
contient vos données commerciales.

---

## Vérifier l'envoi d'email

```bash
# Test complet (recherche + envoi réel du rapport)
docker compose exec app python -m scripts.run_daily
# ou en natif :
sudo -u cordiste /opt/cordiste-prospection-ai/.venv/bin/python -m scripts.run_daily
```

Si l'envoi échoue, vérifiez `SMTP_PASSWORD`, que le port 465 sortant est ouvert,
et que la boîte `contact@cordiste-ile-de-france.fr` existe bien côté LWS.
