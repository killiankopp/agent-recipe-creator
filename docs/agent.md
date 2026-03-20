# Lancer l'agent

L'agent nécessite **deux processus** qui tournent en parallèle.

## Prérequis

- MongoDB sur `localhost:5971`
- Ollama ou LM Studio avec un modèle chargé (min 7B, tool calling requis)

## config.yaml — section `agent`

### Ollama

```bash
ollama run llama3.3:latest
```

```yaml
agent:
  model_name: llama3.3:latest
  base_url: http://localhost:11434/v1
  api_key: ollama
```

### LM Studio

1. Ouvrir LM Studio → onglet **Developer**
2. Charger un modèle compatible tool calling (voir tableau ci-dessous)
3. Démarrer le serveur local (bouton **Start Server**)
4. Copier l'identifiant exact du modèle affiché dans l'onglet Developer

```yaml
agent:
  model_name: qwen/qwen3.5-9b   # identifiant exact affiché dans LM Studio
  base_url: http://localhost:1234/v1
  api_key: lm-studio
```

## Terminal 1 — MCP server

```bash
cd _sample
uv run python main_mcp_http.py
```

Écoute sur `http://127.0.0.1:8001/mcp`.

## Terminal 2 — Agent Chainlit

```bash
cd _sample
uv run chainlit run main_agent.py --port 8002
```

UI disponible sur `http://localhost:8000`.

## Modèles locaux compatibles

| Modèle | Tool calling | Ollama | LM Studio |
|---|---|---|---|
| `llama3.3:latest` | ✅ très bon | ✅ | ✅ |
| `qwen2.5:14b` | ✅ excellent | ✅ | ✅ |
| `qwen2.5:7b` | ✅ bon | ✅ | ✅ |
| `mistral-small` (22B) | ✅ bon | ✅ | ✅ |
| modèles < 7B | ⚠️ instable | — | — |
