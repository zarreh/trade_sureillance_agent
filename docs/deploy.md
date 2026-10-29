# Deploy to a server

How to run the Trade Surveillance Agent on a Linux server behind HTTPS, using
`compose.prod.yaml`. It builds the API and the web app and publishes **no host
ports**: a reverse proxy is the only way in.

The browser talks to one origin. The proxy sends `/api/*` to the API (removing
the `/api` prefix, because the API itself has no such prefix) and everything
else to the web app.

!!! warning "Not yet exercised end to end"
    The steps are adapted from a deployment that was verified for a sibling app.
    For this repository the compose file and both Dockerfiles have been written
    and the API behaviour they rely on is tested, but the images have **not**
    been built or run behind a proxy yet, and HTTPS certificates and DNS have
    not been exercised.

## 1. What you need

- A Linux server with a public IP, reachable by SSH.
- A domain name with an `A` record pointing at the server (for example
  `surveillance.example.com`).
- [Docker Engine](https://docs.docker.com/engine/install/) with the Compose
  plugin (`docker compose version` should work).
- An OpenAI API key.
- Ports **80 and 443** open to the internet, and nothing else except SSH.

## 2. Get the code onto the server

```bash
git clone https://github.com/zarreh/trade_sureillance_agent.git
cd trade_sureillance_agent
```

The continuous-deployment workflow publishes the API image to GitHub Container
Registry but not the web image, and its server-deploy job is still a
placeholder. So this guide builds both images on the server.

## 3. Put the data on the server

The API reads two read-only databases from `data/` (`facts.db`, `policy.db`)
and writes one of its own there at runtime (`runs.db`). `data/` is git-ignored
and excluded from the image, so you have to provide it. Pick one option.

=== "Build it on the server"

    Needs [`uv`](https://docs.astral.sh/uv/) and outbound internet access (it
    downloads SEC EDGAR bulk files; see [Data pipeline](architecture/data-pipeline.md)).

    ```bash
    uv sync --extra dev
    make data
    ```

=== "Build it locally and copy it"

    On the machine where you already ran `make data`, copy **only** the two
    read-only databases:

    ```bash
    rsync -av \
      --include='facts.db' --include='policy.db' \
      --exclude='*' \
      data/ you@your-server:~/trade_sureillance_agent/data/
    ```

    Do not copy `runs.db`: it is the other machine's run history.

The API container runs as user **1000**, so that user must be able to write to
`data/`:

```bash
sudo chown -R 1000:1000 data
```

Without this the API exits at startup with
`sqlite3.OperationalError: unable to open database file`.

## 4. Configure

Create `.env` in the repository root. It is read by `docker compose` for the
API container, and the two `WEB_PUBLIC_*` lines are also used as **build
arguments** for the web image.

```ini
# --- API (runtime) ---
SURVEILLANCE_OPENAI_API_KEY=sk-...
SURVEILLANCE_ENVIRONMENT=production
SURVEILLANCE_FRONTEND_ORIGINS='["https://surveillance.example.com"]'

# --- Web (baked into the JavaScript at build time) ---
WEB_PUBLIC_API_URL=https://surveillance.example.com/api
WEB_PUBLIC_DOCS_URL=https://zarreh.github.io/trade_sureillance_agent/
```

| Variable | Why it matters |
|---|---|
| `SURVEILLANCE_OPENAI_API_KEY` | Without it, runs that need the model fail. |
| `SURVEILLANCE_ENVIRONMENT` | Anything other than `development` switches logs to JSON and stops trusting localhost origins. |
| `SURVEILLANCE_FRONTEND_ORIGINS` | CORS allow-list as a JSON list. Outside `development` this is the only thing trusted. Because the proxy serves the site and the API from one origin the browser does not need CORS, but set it to your public origin anyway. |
| `WEB_PUBLIC_API_URL` | Where the browser calls the API. Must be the **public** URL ending in `/api`. The default, `http://localhost/api`, only works on the server itself. |
| `WEB_PUBLIC_DOCS_URL` | Target of the Docs links. Point it at wherever the documentation site is published. |

Optional: `SURVEILLANCE_LANGSMITH_API_KEY` for tracing,
`SURVEILLANCE_RATE_LIMIT_PER_MINUTE`, `SURVEILLANCE_MAX_REQUEST_BODY_BYTES`.

!!! warning "The two `WEB_PUBLIC_*` values are build-time"
    Next.js inlines them into the bundle. Changing them in `.env` does nothing
    until you rebuild the web image (`docker compose -f compose.prod.yaml up -d --build`).
    A site whose API calls go to `localhost` was built without
    `WEB_PUBLIC_API_URL`.

!!! note "Keep `.env` out of git"
    It holds your API key. It is already git-ignored and excluded from the
    images.

## 5. Set up the reverse proxy

`compose.prod.yaml` attaches both services to an **external** Docker network
named `edge`. Create it once, then run a proxy on it. The services are named
`surveillance-api` and `surveillance-web` so they don't clash with other apps
sharing the network.

```bash
docker network create edge     # skip if it already exists
```

`~/proxy/compose.yaml`:

```yaml
services:
  caddy:
    image: caddy:2
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data        # certificates live here
      - caddy_config:/config
    networks:
      - edge

volumes:
  caddy_data:
  caddy_config:

networks:
  edge:
    external: true
```

`~/proxy/Caddyfile`:

```caddyfile
surveillance.example.com {
        handle_path /api/* {
                reverse_proxy surveillance-api:8000 {
                        flush_interval -1
                }
        }

        handle {
                encode zstd gzip
                reverse_proxy surveillance-web:3000
        }
}
```

- `handle_path` strips `/api` before forwarding. Without it the API sees
  `/api/investigations` and returns 404.
- `flush_interval -1` sends the live run stream through immediately instead of
  buffering it, and `encode` is deliberately kept off the `/api` routes so the
  stream is never compressed into a lump.

Caddy also requests and renews the HTTPS certificate by itself.

??? note "nginx instead of Caddy"

    ```nginx
    location /api/ {
        proxy_pass http://surveillance-api:8000/;   # trailing slash strips /api
        proxy_http_version 1.1;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header Host $host;
        proxy_buffering off;                        # server-sent events
        proxy_read_timeout 120s;
    }
    location / {
        proxy_pass http://surveillance-web:3000;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header Host $host;
    }
    ```

## 6. Start the app

```bash
docker compose -f compose.prod.yaml up -d --build
docker compose -f compose.prod.yaml ps          # both should say "healthy"
curl https://surveillance.example.com/api/healthz
```

The web container waits for the API's health check before it starts. Open the
site and confirm an investigation streams node by node and ends in a finding.

## 7. Protect the site

!!! danger "Do this before the site is public"
    The app has no login, and every investigation spends your model credits.
    The per-client rate limit is a backstop, not access control. Put basic
    auth at the proxy; because the page and its API calls share one origin, one
    rule covers both.

```bash
docker compose -f ~/proxy/compose.yaml exec caddy caddy hash-password
```

```caddyfile
surveillance.example.com {
        basic_auth {
                reviewer <paste-the-hash-here>
        }

        handle_path /api/* {
                # ...unchanged...
        }
        handle {
                # ...unchanged...
        }
}
```

To keep the home page public and protect only the paid endpoint, scope the rule
to `@start method POST` and `path /api/investigations`. Do not put an API key in
browser code: anything in the browser is visible to everyone.

## 8. Operate it

**Logs**

```bash
docker compose -f compose.prod.yaml logs -f surveillance-api
```

**Update to a new version**

```bash
git pull
docker compose -f compose.prod.yaml up -d --build
```

`data/` is untouched. A run in flight during the restart cannot finish; on
startup the API marks it **failed** ("interrupted by a server restart") so the
page shows an error instead of waiting forever.

**Back up**

`facts.db` and `policy.db` are rebuildable with `make data`. Only `runs.db` is
unique to the server:

```bash
mkdir -p backups
sqlite3 data/runs.db ".backup 'backups/runs-$(date +%F).db'"
```

**Run one API process.** Runs execute inside the API process and the store is a
SQLite file, so do not scale `surveillance-api` to several replicas or workers.

**Duplicate starts.** Two `POST /investigations` calls for the same accession
start two independent runs. That is allowed on purpose: runs are replayable
records, and the rate limit bounds the cost.

## 9. Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| API container exits with `unable to open database file` | `data/` is not writable by user 1000. Run `sudo chown -R 1000:1000 data`. |
| The page loads but every start fails, or the browser tries `localhost` | `WEB_PUBLIC_API_URL` was missing or wrong when the web image was built. Fix `.env` and rebuild with `up -d --build`. |
| `404` on every API call through the proxy | The proxy is not stripping `/api`. Use `handle_path` (Caddy) or a trailing slash on `proxy_pass` (nginx). |
| The run seems to hang, then everything appears at once | The proxy is buffering the event stream. Use `flush_interval -1` (Caddy) or `proxy_buffering off` (nginx), and do not compress `/api`. |
| "Accession … is not in the facts database" | The accession is not in `data/facts.db`. Use one from the loaded filings, or rebuild the data. |
| The browser blocks the call (CORS error) | The page's origin is not in `SURVEILLANCE_FRONTEND_ORIGINS`. Add the exact public origin (scheme and host, no path) and restart the API. |
| Everyone gets `429 Too many requests` | The rate limit is per client address. If the proxy does not pass the real client address, all visitors share one bucket. Make the proxy **set** `X-Forwarded-For` (Caddy does by default). |
| Runs fail with an authentication error from the model | `SURVEILLANCE_OPENAI_API_KEY` is missing or wrong. Fix `.env`, then `docker compose -f compose.prod.yaml up -d`. |

## 10. Security notes

- The API trusts `X-Forwarded-For` from any peer (`--forwarded-allow-ips "*"`)
  so the per-client rate limit sees real visitors. That is safe **only** because
  no host port is published and the proxy replaces the header. Never publish
  the API port directly.
- Open only 22, 80 and 443 in the server firewall.
- The trade data is public SEC filings, but the role limits, compliance rules
  and corporate-events calendar are **synthetic**. The app is a research
  prototype, not a supervisory system of record.
