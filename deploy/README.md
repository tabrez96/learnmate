Deployment files (Docker Compose with `server` and `cloudflared`, `.env.example`, runbook) arrive in a later change.

## Embedding model

Set `EMBED_CACHE_DIR=<data dir>/models` so the downloaded model survives container rebuilds. To switch models, change `EMBED_MODEL` in `.env`, then run `docker compose up -d server`. This recreates the container with the new environment, and start-up re-embeds every chunk that still has the old model. Run `docker compose exec server python -m learnmate.rag.reindex` only after that. `docker compose restart` and `exec` keep the container's old environment, so they would use the old model.

Start-up re-embedding is best-effort: if the model can't be loaded (for example it isn't cached and there is no network), the server logs the error and starts anyway. The stale chunks are retried on the next start or by the reindex command.
