# IA intégrée (open source, gratuite)

Le projet peut utiliser un **LLM open source auto-hébergé** pour rendre la
prospection plus intelligente. Aucune API payante n'est requise : on s'appuie
sur **[Ollama](https://ollama.com)**, qui fait tourner des modèles ouverts
(Qwen, Gemma, Llama, Phi…) **localement et gratuitement**.

Comme Ollama expose une API **compatible OpenAI**, le même code fonctionne aussi
avec n'importe quel service compatible (Groq, OpenRouter, LM Studio, vLLM…) : il
suffit de changer `AI_BASE_URL` et `AI_API_KEY`.

## Ce que l'IA apporte

- **Scoring intelligent + justification** : le modèle évalue le potentiel réel de
  chaque entreprise (parc immobilier, façades, hauteur) et écrit une phrase
  d'explication. Le score IA remplace le score par règles quand il répond.
- **Message de prospection** : un brouillon d'accroche personnalisé par prospect.
- **Résumé IA du rapport quotidien** : les meilleurs prospects du jour, résumés.

Tout est **optionnel** : si `AI_ENABLED=false` ou si le modèle est injoignable,
l'application retombe automatiquement sur le scoring par règles. L'IA ne peut
jamais bloquer une recherche.

## Activation avec Docker (recommandé)

```bash
# 1. Démarrer l'app + le service IA
docker compose --profile ai up -d --build

# 2. Télécharger un modèle open source (une seule fois)
docker compose exec ollama ollama pull qwen2.5:3b

# 3. Dans .env :
#    AI_ENABLED=true
#    AI_BASE_URL=http://ollama:11434/v1
#    AI_MODEL=qwen2.5:3b
docker compose up -d        # recharge la config
```

## Activation sans Docker

```bash
# Installer Ollama : https://ollama.com/download
ollama pull qwen2.5:3b
ollama serve                # API sur http://localhost:11434

# Dans .env : AI_ENABLED=true, AI_BASE_URL=http://localhost:11434/v1
```

## Choisir un modèle

| Modèle (Ollama) | Taille | Pour qui |
|-----------------|--------|----------|
| `qwen2.5:3b` | ~2 Go | Léger, multilingue, tourne sur CPU (défaut) |
| `gemma3:4b` | ~3 Go | Très bon multilingue (140+ langues) |
| `llama3.2:3b` | ~2 Go | Bon généraliste léger |
| `phi4-mini` | ~3 Go | Bon raisonnement compact |
| `qwen2.5:7b` | ~5 Go | Plus fin si vous avez la RAM/GPU |

Conseil : testez avec vos vraies données françaises — la qualité varie selon les
modèles. Un petit modèle (3-4B) suffit pour du scoring et des résumés courts, et
fonctionne sur un VPS sans carte graphique (un peu plus lent).

## Coût & confidentialité

- **Gratuit** : les modèles sont open source et tournent chez vous. Aucun coût par
  requête, aucune donnée envoyée à un tiers.
- Si vous préférez un service hébergé compatible OpenAI, renseignez `AI_API_KEY`
  et `AI_BASE_URL` ; la clé reste dans `.env`, jamais sur GitHub.
