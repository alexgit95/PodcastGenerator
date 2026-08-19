# Usage

## 1. Workflow UI recommande

1. Ouvrir l'interface sur `http://localhost:8080`
2. Creer les categories (avec poids)
3. Ajouter les flux RSS
4. Associer categories et flux (mapping)
5. Tester la sante des flux
6. Regler la duree cible
7. Lancer une previsualisation de composition
8. Generer le script via API economique
9. Generer l'audio manuellement ou recuperer le dernier audio genere

## 2. Regles metier en place

- Episode multi-categories pondere
- Fraicheur max des items: 48h
- Duree cible configurable
- Si depassement: coupe conclusion puis transitions puis breves moins prioritaires
- Controle cout: cap tokens/episode + cap budget mensuel
- Provider LLM unique actif a la fois (pas de routage multi-provider simultane)
- Changement de provider via configuration + restart/redeploy

Politique operationnelle provider:

- Une seule configuration provider est lue au demarrage.
- Toutes les generations d'un run utilisent ce meme provider actif.
- Pour changer de provider: mise a jour des variables provider puis restart/redeploy.

## 3. Mode de generation

### Mode LLM

- Utiliser le panneau `Mode generation` pour rester sur `LLM`.
- La configuration provider reste requise (cle, URL, modele, pricing).

### Mode sans LLM

- Basculer le panneau `Mode generation` sur `Sans LLM`.
- La generation utilise la matrice deterministe locale.
- Le panneau `Matrice deterministe` permet de regler la configuration globale et les overrides Tech/Sport/Monde.
- Une categorie nouvellement creee recoit automatiquement un override de base modifiable.

## 4. Endpoints API utiles

### Categories et flux

- `GET /api/categories`
- `POST /api/categories`
- `PUT /api/categories/<id>`
- `DELETE /api/categories/<id>`
- `GET /api/rss-sources`
- `POST /api/rss-sources`
- `PUT /api/rss-sources/<id>`
- `DELETE /api/rss-sources/<id>`
- `POST /api/rss-sources/<id>/health-check`

### Mappings

- `GET /api/mappings`
- `POST /api/mappings`
- `DELETE /api/mappings?category_id=<id>&source_id=<id>`

### Composition et generation

- `POST /api/compose/preview`
- `POST /api/generate/script`
- `POST /api/generate/audio`
- `POST /api/generate/scheduled`
- `GET /api/generate/audio/latest`

### Settings et observabilite

- `GET /api/settings/duration-target`
- `PUT /api/settings/duration-target`
- `GET /api/settings/schedule`
- `PUT /api/settings/schedule`
- `GET /api/budget-status`
- `GET /api/jobs`

## 5. Exemples rapides

### Previsualisation

```bash
curl -X POST http://localhost:8080/api/compose/preview \
  -H "Content-Type: application/json" \
  -d '{"duration_target_minutes": 10}'
```

### Generation script

```bash
curl -X POST http://localhost:8080/api/generate/script \
  -H "Content-Type: application/json" \
  -d '{"duration_target_minutes": 10}'
```

### Generation planifiee (script puis audio)

```bash
curl -X POST http://localhost:8080/api/generate/scheduled \
  -H "Content-Type: application/json" \
  -d '{"duration_target_minutes": 10}'
```

### Recuperer le dernier audio genere

```bash
curl http://localhost:8080/api/generate/audio/latest
```

### Statut budget

```bash
curl http://localhost:8080/api/budget-status
```

## 6. Publication Docker via GitHub Actions

Workflow:

- [.github/workflows/build-and-push.yml](.github/workflows/build-and-push.yml)

Pre-requis repository secrets:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

Resultat attendu selon evenement Git:

- Push sur branche non `main`: publication `${DOCKERHUB_USERNAME}/podcast-generator:<branch-sanitize>`
- Push sur `main`: publication `${DOCKERHUB_USERNAME}/podcast-generator:latest`
- Push git tag `vX.Y.Z`: publication `${DOCKERHUB_USERNAME}/podcast-generator:vX.Y.Z` et `latest`
