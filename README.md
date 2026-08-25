# Crimson Nyx Studios (CNS1)

Creative studio website with FastAPI backend, MongoDB database, and a cinematic dark-themed frontend.

## Prerequisites

- **Python 3.10+**
- **MongoDB** running locally on `mongodb://localhost:27017` (default)

## Setup

```bash
# Install dependencies
python -m pip install -r requirements.txt

# (Optional) Copy and configure environment
copy .env.example .env
# Edit .env with your settings
```

## Run locally

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001
```

Then open:

- `http://127.0.0.1:8001/` — Site
- `http://127.0.0.1:8001/health` — Health check (includes MongoDB status)

## Contact form

Contact submissions are stored in MongoDB:

- Database: `crimson_nyx` (configurable via `MONGO_DB`)
- Collection: `messages`

## Admin page

Admin UI (HTTP Basic auth):

- Open: `http://127.0.0.1:8001/admin`
- Default login: `admin` / `admin123`

### Using bcrypt (recommended for production)

Generate a password hash:

```bash
python -c "from passlib.hash import bcrypt; print(bcrypt.hash('yourpassword'))"
```

Then set in `.env`:

```
ADMIN_USER=youruser
ADMIN_PASS_HASH=$2b$12$...your_hash_here...
```

When `ADMIN_PASS_HASH` is set, plaintext `ADMIN_PASS` is ignored.

### Using plaintext (development only)

```powershell
$env:ADMIN_USER="youruser"
$env:ADMIN_PASS="yourpass"
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001
```

## Configuration

All settings can be configured via environment variables or a `.env` file. See [`.env.example`](.env.example) for the full list.

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | `development` or `production` |
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGO_DB` | `crimson_nyx` | Database name |
| `ADMIN_USER` | `admin` | Admin username |
| `ADMIN_PASS` | `admin123` | Admin password (plaintext fallback) |
| `ADMIN_PASS_HASH` | _(empty)_ | Bcrypt hash (takes precedence) |
| `CORS_ORIGINS` | `["http://localhost:8001", ...]` | Allowed CORS origins |
| `RATE_LIMIT_MAX` | `5` | Max requests per window |
| `RATE_LIMIT_WINDOW` | `600` | Window in seconds (10 min) |
| `MAX_BODY_SIZE` | `1048576` | Max request body (1 MB) |

## Project structure

```
CNS1/
├── .env.example          # Environment variable template
├── requirements.txt      # Python dependencies
├── README.md
├── backend/
│   ├── __init__.py
│   ├── config.py         # Centralised settings (pydantic-settings)
│   ├── db.py             # MongoDB operations (pymongo)
│   ├── main.py           # FastAPI application
│   └── admin.html        # Admin dashboard
└── frontend/
    ├── styles.css         # Shared design system
    ├── animations.css     # Animation library
    ├── animations.js      # Animation engine
    ├── index.html         # Homepage
    ├── services.html      # Services page
    ├── work.html          # Work/portfolio page
    ├── about.html         # About page
    ├── contact.html       # Contact page
    └── *.jpeg / *.png     # Assets
```
