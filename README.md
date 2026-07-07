# БакСигнал backend

FastAPI backend for the Саратов/Энгельс fuel availability MVP.

## Local run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
docker compose up -d db
alembic upgrade head
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

## What is implemented

- Station catalog.
- User fuel observations.
- Current aggregated station fuel status.
- Telegram Mini App `initData` validation helper.
- Subscriptions data model for later bot notifications.

## API surface

- `GET /health`
- `GET /stations?fuel_type=95&district=Ленинский`
- `POST /stations`
- `GET /stations/{station_id}`
- `POST /observations`
- `POST /subscriptions`
- `GET /subscriptions/me`

## Import stations from OSM

```powershell
.\.venv\Scripts\python.exe -m app.scripts.import_osm_stations
```

## Import stations from 2GIS

2GIS is the preferred reference source for a clean Saratov/Engels station directory,
but the public API rules restrict saving/caching API products unless your agreement
allows it. Use dry-run first.

1. Create an API key in 2GIS Platform Manager.
2. Put it into `.env`:

```env
DGIS_API_KEY=...
```

3. Inspect candidates without writing to the database:

```powershell
.\.venv\Scripts\python.exe -m app.scripts.import_2gis_stations
```

4. Write to the database only if your 2GIS terms allow storing this data:

```powershell
.\.venv\Scripts\python.exe -m app.scripts.import_2gis_stations --commit --replace-directory --i-have-2gis-storage-permission
```

## Temporary Mini App tunnel

```powershell
.\tools\cloudflared.exe tunnel --url http://127.0.0.1:5173 --no-autoupdate
```

Use the printed `https://*.trycloudflare.com` URL as `MINI_APP_URL` in `.env`,
then restart `python -m app.bot.main`.

For Mini App requests, send Telegram raw init data in the
`X-Telegram-Init-Data` header. The backend validates it with `TELEGRAM_BOT_TOKEN`.

## Notes

- Statuses are not permanent truth. Each observation receives `expires_at`.
- Anonymous user observations are accepted for development, but with low confidence.
- Subscriptions require a validated Telegram user or explicit `telegram_user_id` in trusted local/admin usage.
