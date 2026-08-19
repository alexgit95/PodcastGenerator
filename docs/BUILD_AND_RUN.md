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
export PODCAST_LLM_PROVIDER="openai"
export PODCAST_LLM_MAX_RETRIES="1"
export PODCAST_LLM_MAX_PROMPT_CHARS="20000"
export PODCAST_LLM_INPUT_CENTS_PER_MILLION="15"
export PODCAST_LLM_OUTPUT_CENTS_PER_MILLION="60"
```

Selection du provider unique actif:

- `PODCAST_LLM_PROVIDER` designe le provider actif runtime.
- Valeurs supportees actuellement: `openai`, `openrouter`, `custom-openai-compatible`.
- L'application n'utilise qu'un seul provider a la fois pour toutes les requetes de generation.

Champs provider-agnostiques a initialiser:

- `PODCAST_LLM_PROVIDER`
- `PODCAST_LLM_API_URL`
- `PODCAST_LLM_API_KEY`
- `PODCAST_LLM_MODEL`
- `PODCAST_LLM_INPUT_CENTS_PER_MILLION`
- `PODCAST_LLM_OUTPUT_CENTS_PER_MILLION`

Procedure de switch provider:

1. Mettre a jour les variables provider (nom, endpoint, key, model, pricing).
2. Redemarrer/redeployer le service.
3. Verifier le statut via `GET /api/budget-status` et un test de generation.

Diagnostics de configuration (fail-fast au startup):

- Provider manquant/non supporte
- Endpoint manquant ou URL invalide
- Modele manquant
- Valeurs invalides pour retries/prompt/pricing

Utilisation du mode generation dans l'interface:

1. Ouvrir le panneau `Mode generation` dans l'administration.
2. Choisir `LLM` ou `Sans LLM` puis sauver le mode.
3. En mode `Sans LLM`, ouvrir `Matrice deterministe` pour ajuster la configuration globale et les overrides par categorie.
4. Chaque nouvelle categorie recoit un override deterministe par defaut, modifiable ensuite dans sa carte.

Utilisation du mode audio dans l'interface:

1. Ouvrir le panneau `Mode generation` dans l'administration.
2. Choisir `Audio local (Piper)` ou `Audio cloud` puis sauver le mode audio.
3. En mode local, le MP3 est genere avec Piper puis un lien de telechargement apparait sous le script.
4. Le telechargement pointe vers le meme ecran que la visualisation du script, pour rester dans un seul flux operateur.

Comportement important:

- En mode `Sans LLM`, la generation ne consomme pas de cle API provider.
- En mode `LLM`, le provider selectionne reste obligatoire et les garde-fous provider/tokens s'appliquent.
- Le changement de mode prend effet apres sauvegarde dans l'UI, sans redeploiement.
- En mode audio local, l'image embarque Piper, ffmpeg et un modele francais: aucune variable audio additionnelle n'est a renseigner sur la machine hote.

Exemple 1: initialisation provider OpenAI

```bash
export PODCAST_LLM_PROVIDER="openai"
export PODCAST_LLM_API_URL="https://api.openai.com/v1/chat/completions"
export PODCAST_LLM_API_KEY="<openai_api_key>"
export PODCAST_LLM_MODEL="gpt-4o-mini"
export PODCAST_LLM_INPUT_CENTS_PER_MILLION="15"
export PODCAST_LLM_OUTPUT_CENTS_PER_MILLION="60"
```

Comment recuperer la cle API OpenAI:

1. Ouvrir la console OpenAI: https://platform.openai.com/
2. Se connecter puis aller dans la section API Keys.
3. Creer une nouvelle cle secrete.
4. Copier la cle au moment de la creation (elle peut ne plus etre affichable en clair ensuite).
5. Renseigner cette valeur dans `PODCAST_LLM_API_KEY`.

Bonnes pratiques:

- Ne jamais commiter la cle dans le depot.
- Definir la cle via variables d'environnement (local) ou secrets (CI/CD, Portainer).

Exemple 2: initialisation provider OpenRouter

```bash
export PODCAST_LLM_PROVIDER="openrouter"
export PODCAST_LLM_API_URL="https://openrouter.ai/api/v1/chat/completions"
export PODCAST_LLM_API_KEY="<openrouter_api_key>"
export PODCAST_LLM_MODEL="openai/gpt-4o-mini"
export PODCAST_LLM_INPUT_CENTS_PER_MILLION="15"
export PODCAST_LLM_OUTPUT_CENTS_PER_MILLION="60"
```

Comment recuperer la cle API OpenRouter:

1. Ouvrir le tableau de bord OpenRouter: https://openrouter.ai/
2. Se connecter puis acceder a la section Keys/API Keys.
3. Generer une nouvelle cle API.
4. Copier la cle puis la definir dans `PODCAST_LLM_API_KEY`.
5. Verifier que le compte/projet est autorise a utiliser le modele configure dans `PODCAST_LLM_MODEL`.

Verification rapide apres configuration:

1. Redemarrer l'application (ou redeployer le conteneur).
2. Appeler `GET /api/budget-status` pour verifier que l'API repond.
3. Lancer `POST /api/generate/script` pour valider la chaine complete.

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

## 9. Exemple manifest Portainer (Stack)

Exemple de stack Portainer (format compose) pour Raspberry Pi.
Le principe est identique pour OpenAI/OpenRouter/custom-openai-compatible: un seul provider actif a la fois.

```yaml
version: "3.8"

services:
  podcast-generator:
    image: ${DOCKERHUB_USERNAME}/podcast-generator:latest
    container_name: podcast-generator
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      PODCAST_LLM_API_KEY: "${PODCAST_LLM_API_KEY}"
      PODCAST_LLM_PROVIDER: "${PODCAST_LLM_PROVIDER}"
      PODCAST_LLM_API_URL: "${PODCAST_LLM_API_URL}"
      PODCAST_LLM_MODEL: "${PODCAST_LLM_MODEL}"
      PODCAST_LLM_MAX_RETRIES: "1"
      PODCAST_LLM_MAX_PROMPT_CHARS: "20000"
      PODCAST_LLM_INPUT_CENTS_PER_MILLION: "${PODCAST_LLM_INPUT_CENTS_PER_MILLION}"
      PODCAST_LLM_OUTPUT_CENTS_PER_MILLION: "${PODCAST_LLM_OUTPUT_CENTS_PER_MILLION}"
    volumes:
      - podcast_data:/app/data

volumes:
  podcast_data:
    driver: local
```

Notes:

- Renseigner `DOCKERHUB_USERNAME`, `PODCAST_LLM_API_KEY`, `PODCAST_LLM_PROVIDER`, `PODCAST_LLM_API_URL`, `PODCAST_LLM_MODEL`, `PODCAST_LLM_INPUT_CENTS_PER_MILLION`, `PODCAST_LLM_OUTPUT_CENTS_PER_MILLION` dans les variables Portainer.
- Aucun parametre Piper/ffmpeg n'est necessaire dans le cas standard, car ils sont deja inclus dans l'image.
- Le volume `podcast_data` persiste la base SQLite (`/app/data/podcast.db`).
- Si tu veux une version specifique, remplace `latest` par un tag git publie par la CI.
- Pour changer de provider, modifie les variables provider puis redeploie la stack Portainer.

Exemple Portainer pour audio local avec Piper:

```yaml
version: "3.8"

services:
  podcast-generator:
    image: ${DOCKERHUB_USERNAME}/podcast-generator:latest
    container_name: podcast-generator
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      PODCAST_LLM_API_KEY: "${PODCAST_LLM_API_KEY}"
      PODCAST_LLM_PROVIDER: "openai"
      PODCAST_LLM_API_URL: "https://api.openai.com/v1/chat/completions"
      PODCAST_LLM_MODEL: "gpt-4o-mini"
      PODCAST_LLM_MAX_RETRIES: "1"
      PODCAST_LLM_MAX_PROMPT_CHARS: "20000"
      PODCAST_LLM_INPUT_CENTS_PER_MILLION: "15"
      PODCAST_LLM_OUTPUT_CENTS_PER_MILLION: "60"
    volumes:
      - podcast_data:/app/data

volumes:
  podcast_data:
    driver: local
```

Dans cet exemple:

- `piper`, `ffmpeg` et le modele francais sont deja inclus dans l'image
- le volume `podcast_data` ne sert qu'a la base SQLite et aux sorties generees
- si tu veux changer de voix Piper, il faudra reconstruire l'image avec un autre modele

Jeux de variables Portainer (exemples):

OpenAI:

- `PODCAST_LLM_PROVIDER=openai`
- `PODCAST_LLM_API_URL=https://api.openai.com/v1/chat/completions`
- `PODCAST_LLM_MODEL=gpt-4o-mini`
- `PODCAST_LLM_INPUT_CENTS_PER_MILLION=15`
- `PODCAST_LLM_OUTPUT_CENTS_PER_MILLION=60`

OpenRouter:

- `PODCAST_LLM_PROVIDER=openrouter`
- `PODCAST_LLM_API_URL=https://openrouter.ai/api/v1/chat/completions`
- `PODCAST_LLM_MODEL=openai/gpt-4o-mini`
- `PODCAST_LLM_INPUT_CENTS_PER_MILLION=15`
- `PODCAST_LLM_OUTPUT_CENTS_PER_MILLION=60`

## 10. Depannage rapide

- Erreur `Missing API key`: definir `PODCAST_LLM_API_KEY`
- Erreur `Missing provider selection` ou `Unsupported provider`: verifier `PODCAST_LLM_PROVIDER` (`openai`, `openrouter`, `custom-openai-compatible`)
- Erreur `Invalid provider endpoint`: verifier `PODCAST_LLM_API_URL` (doit commencer par `http://` ou `https://`)
- Erreur `Missing provider model`: definir `PODCAST_LLM_MODEL`
- Erreurs `Invalid integer` ou `must be >= 0`/`must be > 0`: corriger les variables `PODCAST_LLM_MAX_RETRIES`, `PODCAST_LLM_MAX_PROMPT_CHARS`, `PODCAST_LLM_INPUT_CENTS_PER_MILLION`, `PODCAST_LLM_OUTPUT_CENTS_PER_MILLION`
- Changement de provider non pris en compte: redeployer/redemarrer apres modification des variables Portainer
- Pas de contenu en preview: verifier mappings categorie->flux et sources actives
- Audio local indisponible: reconstruire/redeloyer l'image pour verifier que Piper, ffmpeg et le modele francais ont bien ete embarques au build
- Budget bloque: consulter endpoint `/api/budget-status`
- Python introuvable: installer Python et relancer l'environnement virtuel
