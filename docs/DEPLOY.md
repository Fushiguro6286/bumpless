# Deploying the hosted demo

Live: https://bumpless.onrender.com (Render free plan, no API keys: replays only).

The `Dockerfile` at the repo root builds the web app (API + frontend). Checked locally with no API keys: the
home page, run pages, benchmarks, recipes and all 4 recorded runs work, and live runs are refused with a clear
message. Live runs inside the container (keys set) have not been run yet.

```bash
docker build -t bumpless-web .
docker run -p 8000:8000 bumpless-web            # replays only
docker run -p 8000:8000 --env-file .env bumpless-web   # + live runs on bundled fixtures
```

The container sets `EXECUTOR=local` (no Docker inside it). The API only runs bundled fixtures live, never user
repos. Set `DEMO_PASSWORD` to restrict live runs, and `DEMO_DAILY_BUDGET_USD` to cap daily spend.

## Option A: Render (free)

1. Open https://render.com/deploy?repo=https://github.com/Fushiguro6286/bumpless and sign in with GitHub.
2. Render reads `render.yaml`. Leave the keys empty for a replay-only demo, or add them for live runs.
3. Click **Apply**. The first build takes a few minutes. The URL looks like `https://bumpless-xxxx.onrender.com`.

The free plan sleeps after 15 minutes idle; the first visit after that takes about a minute to wake up. Open the
URL a minute before demoing.

## Option B: Nebius Serverless AI endpoint (paid, uses Nebius credits)

Needs the Nebius CLI (`nebius profile create` to log in) and the image in a registry Nebius can pull from.

```bash
docker tag bumpless-web <registry>/bumpless-web:1 && docker push <registry>/bumpless-web:1
nebius ai endpoint create --name bumpless --image <registry>/bumpless-web:1 --container-port 8000 \
  --platform <CPU_platform_ID> --preset <CPU_preset> --disk-size 20Gi \
  --env "DEMO_DAILY_BUDGET_USD=2.00" --env-secret ...   # keys via SecretStash
nebius ai endpoint get <endpoint_ID> --format json | jq -r '.status.public_endpoints[] | select(startswith("https://"))'
```

CPU platform and preset IDs: https://docs.nebius.com/compute/virtual-machines/types. Not tried yet.
