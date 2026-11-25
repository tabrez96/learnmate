# Running the server at home

Two containers run on your own computer: `server` (the app's API, the Telegram bot and the watchdog) and `cloudflared` (the Cloudflare Tunnel). Nothing is opened on your router: the tunnel only makes outbound connections. All data (database, uploaded files, downloaded models) lives in `deploy/data/`.

## What you need

- A Linux computer that stays on
- Docker Engine with the Compose plugin
- A domain whose DNS is on Cloudflare
- An Anthropic API key
- A Telegram bot token from @BotFather

Every command below runs in `deploy/` unless stated.

## 1. Create the tunnel and hostname

1. In the Cloudflare dashboard open Zero Trust > Networks > Tunnels > Create a tunnel > Cloudflared.
2. Name it `learnmate`.
3. Copy the token from the `docker run` command shown (the long value after `--token`).
4. Under "Public hostnames" add a hostname such as `learnmate.example.com`, type `HTTP`, URL `server:8000`.

The token gives control of the tunnel, so treat it as a secret.

## 2. Fill in .env

```sh
cp .env.example .env
chmod 600 .env
```

- `CLOUDFLARE_TUNNEL_TOKEN`: the token from step 1.
- `DEVICE_TOKEN`: make one with `openssl rand -hex 32`.
- `ANTHROPIC_API_KEY`: your Anthropic API key.
- `LLM_MONTHLY_BUDGET_USD`: the monthly AI spending cap in USD.
- `TELEGRAM_BOT_TOKEN`: the token from @BotFather.
- `TIMEZONE`: your IANA time zone, e.g. `Europe/London`.
- `PIN_KEY`: a Fernet key that encrypts the stored session PIN. Build the image first, then make a key:

  ```sh
  docker compose build server
  docker compose run --rm server python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

- `EMBED_MODEL` and `RERANK_ENABLED`: leave the defaults unless you are switching models (see below).

Put the same values into `android/local.properties` before building the app:

```properties
learnmate.deviceToken=<DEVICE_TOKEN>
learnmate.serverUrl=https://<hostname>
```

If either key is missing, the app builds with an empty token or a localhost URL.

## 3. Start

```sh
docker compose up -d --build
docker compose ps               # server shows "healthy" after about a minute
docker compose logs -f server
```

Database migrations run on every start. `restart: always` brings both containers back after a reboot as long as Docker starts on boot:

```sh
sudo systemctl enable docker
```

## 4. Keep the computer awake

```sh
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
```

Undo it with `sudo systemctl unmask ...` and the same targets.

On a laptop also set `HandleLidSwitch=ignore` in `/etc/systemd/logind.conf`, then `sudo systemctl restart systemd-logind`. On a desktop, turn off automatic suspend in the power settings. The screen may still turn off.

## 5. Check the tunnel

```sh
curl https://learnmate.example.com/api/v1/health
# {"status":"ok"}
DEVICE_TOKEN=$(grep '^DEVICE_TOKEN=' .env | cut -d= -f2-)
curl -i -H "Authorization: Bearer $DEVICE_TOKEN" https://learnmate.example.com/api/v1/family   # 404 before setup, 200 after
curl -i https://learnmate.example.com/api/v1/family                                            # 401
```

With the token, a 404 ("Family not set up") on a fresh install and a 200 after setup both mean the token works. Only a 401 means it doesn't.

If the health check fails, run `docker compose logs cloudflared` and look for "Registered tunnel connection", and check that the tunnel shows "Healthy" in the dashboard.

## Changing the AI budget

Edit `LLM_MONTHLY_BUDGET_USD` in `.env`, then recreate the container (`docker compose restart` would keep the old value):

```sh
docker compose up -d server
```

The budget month follows `TIMEZONE`. Telegram alerts arrive at 80% and 100%.

## Switching the embedding model

To switch models, change `EMBED_MODEL` in `.env`, then run `docker compose up -d server`. This recreates the container with the new environment, and start-up re-embeds every chunk that still has the old model. Run `docker compose exec server python -m learnmate.rag.reindex` only after that. `docker compose restart` and `exec` keep the container's old environment, so they would use the old model.

Start-up re-embedding is best-effort: if the model can't be loaded (for example it isn't cached and there is no network), the server logs the error and starts anyway. The stale chunks are retried on the next start or by the reindex command.

```sh
# after editing EMBED_MODEL in .env
docker compose up -d server
docker compose ps    # wait until server shows "healthy"; start-up re-embedding runs first
docker compose exec server python -m learnmate.rag.reindex
```

Running the reindex before the server is healthy starts a second re-embed alongside the start-up one.

Then re-tune `RAG_MIN_SIMILARITY` for the new model with the retrieval eval (`docs/retrieval-eval.md`). The eval runs on the host and does not read `deploy/.env`, so pass the new model yourself, from `server/`:

```sh
EMBED_MODEL=<new model> EMBED_CACHE_DIR=~/.cache/fastembed pytest tests/rag -s
```

Use that run's results to choose `RAG_MIN_SIMILARITY`.

## Updating

```sh
git pull
docker compose pull cloudflared
docker compose up -d --build
```

## Stopping

```sh
docker compose down
```

The data in `deploy/data/` stays.
