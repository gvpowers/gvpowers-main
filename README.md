# GV POWERS — Corporate Website

Official corporate website for **GV POWERS** (est. 1997) — *Powering A Better Tomorrow*.
Fifteen complete, selectable design systems on shared content — glassmorphism lives in
exactly one theme (09). Default theme: **Swiss Editorial** (non-glass typographic editorial).
Built with Flask, Jinja2, vanilla CSS/JS and SQLite.

**Main site:** https://gvpowers.in  ·  **Product catalogue:** https://catalog.gvpowers.in

---

## Features

- 15 swappable design systems: Swiss Editorial, Luxury Heritage, Industrial Modern,
  Corporate Minimal, Energy Technology, Dark Graphite, Warm Monochrome, Swiss Grid,
  Glassmorphism Pro (the one glass theme), Neo-Brutalist, Classic Business,
  Spatial Modern, Nordic Minimal, High-End Technology, Modern Energy Portfolio
- Public theme selector (appearance menu) with instant previews; visitor preference
  stored in localStorage; server default set in the admin panel; legacy theme ids are
  migrated automatically
- Hero layout: left-aligned, upper-middle composition, no dead space; solid
  cards/floating badge by default (glass removed as the default language)
- Typographic service/stat presentation — no decorative pictogram chips
- Pages: Home, About, Solutions, Solar, UPS Systems, Generators, Projects, Contact, 404, 500
- Working enquiry form: CSRF protection, honeypot, server-side validation,
  per-IP rate limiting, SQLite storage, and email dispatch to the company
  inbox + thank-you mail to the sender (see `mailer.py`; requires `SMTP_*`
  via `.env` — the service file references this file)
- Password-only admin panel: dynamic project counts, project CRUD, enquiries,
  map locations, default-theme setting (with automatic legacy migration)
- SEO: meta/OG/Twitter tags, canonical URLs, sitemap.xml, robots.txt,
  Schema.org LocalBusiness JSON-LD
- Strict Content-Security-Policy with per-request nonces + security headers
- Real photography from Pexels (downloaded & locally hosted, licence documented
  in [IMAGE_SOURCES.md](IMAGE_SOURCES.md))
- Responsive down to 360px, accessible (skip links, focus states, reduced-motion support)
- Animated statistics counters, scroll reveals, subtle hero parallax

## Quick start (local development)

```bash
cd gvpowers-corporate-website

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

The SQLite database (`instance/enquiries.db`) is created automatically on first run.

## Environment variables

Copy `.env.example` to `.env` and adjust. Key variables:

| Variable | Purpose | Default |
|---|---|---|
| `FLASK_ENV` | `development` or `production` | `development` |
| `SECRET_KEY` | Session signing key — **must set in production** | random per start |
| `SITE_URL` | Canonical site origin (SEO) | `https://gvpowers.in` |
| `CATALOGUE_URL` | Product catalogue origin | `https://catalog.gvpowers.in` |
| `SESSION_COOKIE_SECURE` | HTTPS-only cookies | `false` (dev) / `true` (prod) |
| `DATABASE_PATH` | SQLite file location | `instance/enquiries.db` |
| `ENQUIRY_RATE_LIMIT` / `ENQUIRY_RATE_WINDOW` | Form throttle | `5` / `900` s |
| `SMTP_*` | Host/port/user/app-password for enquiry email dispatch | unset |
| `LOG_FILE` | Optional rotating log | unset |

## Running tests

```bash
pytest -v
```

Covers: every route, navigation links, catalogue integration, security headers,
CSP nonces, image availability, 404 handling, and the full contact-form pipeline
(validation, CSRF, honeypot, sanitisation, rate limiting, database storage).

## Production deployment (Ubuntu server)

The catalogue (`catalog.gvpowers.in`) is a separate application — this guide only
touches `gvpowers.in` and does not modify existing services.

```bash
# 1. Code + environment
sudo mkdir -p /var/www/gvpowers-corporate-website
sudo chown $USER /var/www/gvpowers-corporate-website
git clone <your-repo> /var/www/gvpowers-corporate-website   # or upload the ZIP
cd /var/www/gvpowers-corporate-website

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Configuration
cp .env.example .env
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" >> .env
# Edit .env: FLASK_ENV=production, SESSION_COOKIE_SECURE=true, LOG_FILE=/var/log/gvpowers/app.log
#            SMTP_*  -> required for enquiry email dispatch (systemd loads this file
#            via EnvironmentFile; a missing .env on the server is the usual cause
#            of "SMTP not working" in production)

# 3. Log directory
sudo mkdir -p /var/log/gvpowers && sudo chown www-data:www-data /var/log/gvpowers

# 4. Database (created automatically on first start; to do it explicitly):
cd /var/www/gvpowers-corporate-website && .venv/bin/python -c "from app import create_app; create_app()"

# 5. Smoke test with Gunicorn
cd /var/www/gvpowers-corporate-website
.venv/bin/gunicorn -c gunicorn.conf.py app:app          # listens on 127.0.0.1:8000
curl -s http://127.0.0.1:8000/healthz                   # {"status":"ok"}

# 6. systemd
sudo cp deploy/gvpowers.service /etc/systemd/system/gvpowers.service
#   -> edit User/WorkingDirectory/EnvironmentFile paths inside first
sudo systemctl daemon-reload
sudo systemctl enable --now gvpowers
sudo systemctl status gvpowers

# 7. Nginx
sudo cp deploy/nginx-gvpowers.conf /etc/nginx/sites-available/gvpowers.in
sudo ln -s /etc/nginx/sites-available/gvpowers.in /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 8. HTTPS via Cloudflare — proxy gvpowers.in to this server (DNS + "Full (strict)"
#    SSL mode recommended, origin certificate installed in Nginx if terminating TLS
#    locally; with Cloudflare Tunnel, route the hostname to http://localhost:8000
#    and skip Nginx entirely).
```

### Cloudflare Tunnel option

If the server sits behind `cloudflared`, no Nginx/public port is needed:

```yaml
# ~/.cloudflared/config.yml (excerpt)
ingress:
  - hostname: gvpowers.in
    service: http://localhost:8000
  - hostname: www.gvpowers.in
    service: http://localhost:8000
  - service: http_status:404
```

`cloudflared` must be configured as its own service; this project does not modify
the existing tunnel configuration beyond adding the two hostnames above.

### Images

All photography is committed in `static/images/` — no external hotlinks, so
deployment is just a file copy. To refresh or replace an image, drop the new
file in place (keep the filename) and update `IMAGE_SOURCES.md`.

### Backups

The only state is SQLite: back up `instance/enquiries.db` periodically, e.g.:

```bash
sqlite3 /var/www/gvpowers-corporate-website/instance/enquiries.db \
  ".backup '/backups/enquiries-$(date +%F).db'"
```

Add that line to a daily cron job. Also back up the `.env` file separately.

### Enquiries

Enquiries are stored in `instance/enquiries.db` (table `enquiries`). To export:

```bash
sqlite3 -header -csv instance/enquiries.db "SELECT * FROM enquiries ORDER BY id DESC;"
```

## Project structure

```
gvpowers-corporate-website/
├── app.py                  # Flask application entry point
├── config.py               # Environment-based configuration
├── database.py             # SQLite helpers (enquiries)
├── security.py             # CSRF + rate limiting
├── site_data.py            # Verified company facts & content data
├── icons.py                # Inline SVG icon system
├── gunicorn.conf.py        # Production server config
├── requirements.txt
├── .env.example
├── IMAGE_SOURCES.md        # Photo licence register
├── routes/
│   ├── main.py             # Pages, sitemap, robots, health
│   ├── contact.py          # Enquiry endpoint
│   ├── admin.py            # Password-only admin panel, project CRUD
│   └── themes.py           # 15-theme registry + legacy id migration
├── templates/              # base + 10 page templates + admin/
├── static/
│   ├── css/  (style, animations, responsive, map, css/themes/ with 15 theme files)
│   ├── js/   (header, main, animations, interactions, theme)
│   ├── images/ (hero, solar, ups, generators, projects, about, branding)
│   └── favicon/
├── instance/               # SQLite database (created at runtime)
├── deploy/                 # systemd + nginx configs
└── tests/                  # pytest suite
```

## Content that still requires company confirmation

- Verified street addresses for Chennai & Salem (the historical Salem address is
  shown with an explicit "to be confirmed" note)
- Google Maps embed (blocked until addresses are verified)
- Individual project names/clients/capacities — the Projects page uses clearly
  labelled placeholders that an administrator can populate in `site_data.py`
- Real social media URLs (none are displayed, none invented)
