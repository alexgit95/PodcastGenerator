# Build And Run

## 1. Prerequis

- Python 3.11+ installe sur la machine
- Acces reseau sortant vers les flux RSS
- Cle API pour la generation de script (option 2 economique)

## 2. Installation

Depuis la racine du projet:

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

## 3. Variables d'environnement

Variables minimales recommandees:

```bash
export PODCAST_LLM_API_KEY="<ta_cle_api>"
```

Variables optionnelles:

```bash
export PODCAST_LLM_API_URL="https://api.openai.com/v1/chat/completions"
export PODCAST_LLM_MODEL="gpt-4o-mini"
export PODCAST_LLM_PROVIDER="economical-fr"
export PODCAST_LLM_MAX_RETRIES="1"
export PODCAST_LLM_MAX_PROMPT_CHARS="20000"
export PODCAST_LLM_INPUT_CENTS_PER_MILLION="15"
export PODCAST_LLM_OUTPUT_CENTS_PER_MILLION="60"
```

## 4. Initialisation base

La base SQLite est creee automatiquement au demarrage via le schema:

- [database/schema.sql](database/schema.sql)

Le fichier SQLite final est stocke dans:

- `data/podcast.db`

## 5. Lancement application

```bash
python -m app.main
```

Par defaut:

- URL: http://localhost:8080

## 6. Lancer les tests

```bash
python -m unittest discover -s tests -t . -p "test_*.py"
```

## 7. Build conteneur (optionnel)

Exemple minimal de build/run Docker:

```bash
docker build -t podcast-generator:local .
docker run --rm -p 8080:8080 \
  -e PODCAST_LLM_API_KEY="<ta_cle_api>" \
  podcast-generator:local
```

Le build utilise le Dockerfile versionne a la racine du depot:

- [Dockerfile](Dockerfile)

## 8. CI/CD GitHub Actions vers Docker Hub

Workflow CI/CD:

- [.github/workflows/build-and-push.yml](.github/workflows/build-and-push.yml)

Secrets GitHub requis:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

Politique de tags image:

- push sur branche non `main`: tag image = nom de branche sanitize
- push sur `main`: tag image = `latest`
- push d'un git tag: tags image = `<git-tag>` et `latest`

Image publiee:

- `${DOCKERHUB_USERNAME}/podcast-generator:<tag>`

## 9. Depannage rapide

- Erreur `Missing API key`: definir `PODCAST_LLM_API_KEY`
- Pas de contenu en preview: verifier mappings categorie->flux et sources actives
- Budget bloque: consulter endpoint `/api/budget-status`
- Python introuvable: installer Python et relancer l'environnement virtuel
