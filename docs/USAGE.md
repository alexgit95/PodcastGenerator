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

## 2. Regles metier en place

- Episode multi-categories pondere
- Fraicheur max des items: 48h
- Duree cible configurable
- Si depassement: coupe conclusion puis transitions puis breves moins prioritaires
- Controle cout: cap tokens/episode + cap budget mensuel

## 3. Endpoints API utiles

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

### Settings et observabilite

- `GET /api/settings/duration-target`
- `PUT /api/settings/duration-target`
- `GET /api/settings/schedule`
- `PUT /api/settings/schedule`
- `GET /api/budget-status`
- `GET /api/jobs`

## 4. Exemples rapides

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

### Statut budget

```bash
curl http://localhost:8080/api/budget-status
```

## 5. Publication Docker via GitHub Actions

Workflow:

- [.github/workflows/build-and-push.yml](.github/workflows/build-and-push.yml)

Pre-requis repository secrets:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

Resultat attendu selon evenement Git:

- Push sur branche non `main`: publication `${DOCKERHUB_USERNAME}/podcast-generator:<branch-sanitize>`
- Push sur `main`: publication `${DOCKERHUB_USERNAME}/podcast-generator:latest`
- Push git tag `vX.Y.Z`: publication `${DOCKERHUB_USERNAME}/podcast-generator:vX.Y.Z` et `latest`
