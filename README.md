# Composearch

Composearch is a price comparison web app that combines the functionalities of a web scraper and a meta search engine. It allows you to search for products using either a product code or a keyword. Composearch utilizes its integrated web scraping capabilities to crawl and extract data from a predefined list of online stores. The application then presents the search results in a user-friendly table format, sorted by price for convenient comparison.

<img src="/composearch.png" width=75% alt="Composearch Preview"/>

You can see it up and running, deployed on Railway: https://composearch.up.railway.app

## Technologies Used

- **Python**: Powers the backend functionality of Composearch.
- **Django**: Provides a robust framework for building the web application.
- **Django Channels**: Streams search results to the browser via Server-Sent Events.
- **PostgreSQL**: Stores and manages distributor data, integrated via psycopg 3.
- **Playwright**: Enables efficient web scraping and data extraction from online stores.
- **BeautifulSoup**: Facilitates HTML parsing and data extraction from web pages.
- **Redis**: Implements cache-aside (lazy loading) strategy for improved performance and serves as the Celery broker.
- **Celery**: Runs background tasks to keep the top search queries up to date.
- **TailwindCSS**: Enhances the visual aesthetics and responsiveness of the application.
- **Poetry**: Manages the project's dependencies and package management.

## Test Coverage Report

| Name | Stmts | Miss | Cover |
|------|-------|------|-------|
| composearch\\_\_init\_\_.py | 2 | 0 | 100% |
| composearch\asgi.py | 8 | 8 | 0% |
| composearch\celery.py | 8 | 0 | 100% |
| composearch\settings.py | 41 | 7 | 83% |
| composearch\urls.py | 3 | 0 | 100% |
| composearch\wsgi.py | 4 | 4 | 0% |
| search\\_\_init\_\_.py | 0 | 0 | 100% |
| search\admin.py | 88 | 2 | 98% |
| search\apps.py | 4 | 0 | 100% |
| search\consumers.py | 23 | 0 | 100% |
| search\management\\_\_init\_\_.py | 0 | 0 | 100% |
| search\management\commands\\_\_init\_\_.py | 0 | 0 | 100% |
| search\management\commands\sync_distributors.py | 95 | 1 | 99% |
| search\migrations\0001_initial.py | 5 | 0 | 100% |
| search\migrations\0002_distributorsourcemodel_product_currency_selector.py | 4 | 0 | 100% |
| search\migrations\0003_remove_distributorsourcemodel_product_currency_selector_and_more.py | 4 | 0 | 100% |
| search\migrations\0004_distributorsourcemodel_active.py | 4 | 0 | 100% |
| search\migrations\0005_remove_distributorsourcemodel_including_vat_and_more.py | 4 | 0 | 100% |
| search\migrations\0006_distributorsourcemodel_probe_query_distributorstats.py | 5 | 0 | 100% |
| search\migrations\\_\_init\_\_.py | 0 | 0 | 100% |
| search\models.py | 45 | 0 | 100% |
| search\parsers\\_\_init\_\_.py | 4 | 0 | 100% |
| search\parsers\base.py | 43 | 9 | 79% |
| search\parsers\bs4_parser.py | 27 | 0 | 100% |
| search\parsers\playwright_parser.py | 31 | 2 | 94% |
| search\services\\_\_init\_\_.py | 5 | 0 | 100% |
| search\services\browser_service.py | 110 | 8 | 93% |
| search\services\fetcher.py | 76 | 0 | 100% |
| search\services\monitoring.py | 39 | 0 | 100% |
| search\services\probes.py | 48 | 3 | 94% |
| search\services\product.py | 55 | 0 | 100% |
| search\services\search_service.py | 49 | 4 | 92% |
| search\services\stats.py | 41 | 11 | 73% |
| search\tasks.py | 13 | 0 | 100% |
| search\tests\\_\_init\_\_.py | 0 | 0 | 100% |
| search\tests\fixtures\playwright.py | 75 | 2 | 97% |
| search\tests\fixtures\products.py | 5 | 0 | 100% |
| search\tests\parsers\\_\_init\_\_.py | 0 | 0 | 100% |
| search\tests\parsers\test_base.py | 19 | 1 | 95% |
| search\tests\parsers\test_bs4_parser.py | 35 | 0 | 100% |
| search\tests\parsers\test_playwright_parser.py | 35 | 0 | 100% |
| search\tests\services\\_\_init\_\_.py | 0 | 0 | 100% |
| search\tests\services\test_browser_manager.py | 94 | 5 | 95% |
| search\tests\services\test_fetcher.py | 124 | 0 | 100% |
| search\tests\services\test_monitoring.py | 88 | 0 | 100% |
| search\tests\services\test_perform_search.py | 21 | 0 | 100% |
| search\tests\services\test_probes.py | 95 | 0 | 100% |
| search\tests\services\test_product.py | 40 | 0 | 100% |
| search\tests\services\test_stats.py | 49 | 0 | 100% |
| search\tests\services\test_stream_search.py | 102 | 0 | 100% |
| search\tests\test_admin.py | 118 | 0 | 100% |
| search\tests\test_consumers.py | 45 | 0 | 100% |
| search\tests\test_distributors.py | 9 | 0 | 100% |
| search\tests\test_models.py | 99 | 0 | 100% |
| search\tests\test_sync_distributors.py | 108 | 0 | 100% |
| search\tests\test_tasks.py | 35 | 0 | 100% |
| search\tests\test_views.py | 78 | 0 | 100% |
| search\tests\utils\\_\_init\_\_.py | 0 | 0 | 100% |
| search\tests\utils\test_helpers.py | 15 | 0 | 100% |
| search\urls.py | 3 | 0 | 100% |
| search\utils\\_\_init\_\_.py | 2 | 0 | 100% |
| search\utils\helpers.py | 10 | 0 | 100% |
| search\views.py | 43 | 4 | 91% |
| **TOTAL** | **2235** | **71** | **97%** |

## Quick Start

##### Prerequisites

- Python 3.11.5+
- Poetry
- Redis (optional)
- PostgreSQL (optional)

##### 1. Checkout the project from github

```
git checkout https://github.com/enev13/composearch.git
```

##### 2. Rename .env.sample file in the project folder to .env and edit the environment variables if necessary.

```
mv .env.sample .env
nano .env
```

##### 3. Install the project dependencies

```
poetry install
```

##### 4. Initialize Playwright (it will install Chromium and other dependencies)

```
playwright install --with-deps chromium
```

##### 5. Initialize the Django app

```
python manage.py migrate
python manage.py collectstatic
python manage.py createsuperuser
uvicorn composearch.asgi:application --reload
```

##### 6. Fill in some Distributor data

by either creating new database entries using Django admin

```
http://127.0.0.1:8000/admin
```

or by loading the supplied fixtures file
```
python manage.py loaddata distributors.json
```

(See more details below about the Distributor data format.)

`loaddata` is only for the initial seeding of an empty database. If you later edit the fixture (add, remove or update distributors), keep the database in sync with the `sync_distributors` command instead of re-running `loaddata`, which would create duplicate entries:

```
python manage.py sync_distributors
```

(See more details below about keeping the distributor list in sync.)

##### 7. Open Composearch in your web browser

```
http://127.0.0.1:8000/
```

## Deployment

### Local Docker

The full stack (web, nginx, PostgreSQL, Redis, Celery) runs with a single command:

```
cp .env.sample .env
docker compose up --build
```

Then open http://localhost/ - nginx on host port 80 is the single published entry point and proxies to uvicorn, whose port 8000 stays internal to the compose network. The Django admin is at http://localhost/admin/, logging in with the `DJANGO_SUPERUSER_*` credentials from `.env` (the superuser is created automatically on startup when missing).

Notes:

- All five services have healthchecks; `docker compose ps` shows them `(healthy)` once the stack is up.
- The app exposes a `/health/` endpoint (database, cache, and browser state) that the compose healthchecks use — handy for a quick check of any deployment.
- Database data survives container restarts by default. Set `RESET_DB_ON_START=true` in `.env` to restore the old wipe-and-reseed-on-every-start behavior.
- After changing dependencies in `pyproject.toml` / `poetry.lock`, run `docker compose up --build --renew-anon-volumes` so the anonymous `/app/.venv` volume picks up the new packages.
- `SECRET_KEY` values must not contain `$`: docker compose interpolates `$...` sequences inside `env_file` values, and the container would receive a different key than the file.

### Railway

Railway builds the Dockerfile directly (docker-compose.yaml and nginx are compose-only there); TLS terminates at Railway's edge. Set these Variables in the service:

| Variable | Value |
| --- | --- |
| `PRODUCTION` | `True` |
| `SECRET_KEY` | random `[A-Za-z0-9]` string (no `$`) |
| `ALLOWED_HOSTS` | `composearch.up.railway.app` |
| `CSRF_TRUSTED_ORIGINS` | `https://composearch.up.railway.app` (scheme required, no trailing slash) |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_HOST` / `POSTGRES_DB` / `POSTGRES_NAME` / `POSTGRES_PORT` | Railway Postgres reference values |
| `REDIS_URL` | Railway Redis reference URL |
| `DJANGO_SUPERUSER_USERNAME` / `_EMAIL` / `_PASSWORD` | optional; admin auto-created from env on first boot |
| `RESET_DB_ON_START` | optional; `true` = wipe + reseed on every deploy |

`PRODUCTION=True` additionally sets `SECURE_PROXY_SSL_HEADER` (Django trusts Railway's `X-Forwarded-Proto`) and marks session/CSRF cookies `Secure`. The startup log prints the effective mode (`PRODUCTION=...` plus the DB engine), so a deploy that forgot `PRODUCTION=True` is easy to spot in the deploy logs.

### Self-hosting with HTTPS (compose)

nginx listens on port 80 and carries commented TLS scaffolding: drop a certificate and key into `./certs/`, uncomment the four `ssl` lines in `nginx.conf`, and republish the port (e.g. `443:443`). The `./certs` mount is already wired in docker-compose.yaml; the directory is git- and docker-ignored so private keys never enter the repo or the image.

## The DistributorSourceModel

In order to have a fully functional app, the database must be populated with distributor data.
For each online store following data is needed:

- name - name of the distributor, e.g. _BestParts_
- base_url - base url with trailing slash, e.g. *https://www.bestparts.com/*
- search_string - the rest of the search address, e.g. *search?q=%s* , where %s is in the place of the search term
- currency - the currency in which the distributor's site operate, e.g. EUR, USD, GBP, etc.
- included_vat - the VAT percentage included in the price. Used to calculate the net price, which will be displayed
- product_name_selector - CSS selector for the product name in the search results
- product_url_selector - CSS selector for the product url in the search results
- product_picture_url_selector - CSS selector for the ulr of the product picture in the search results
- product_price_selector - CSS selector for the product price in the search results
- price_on_detail_page - when true, the product link found on the search results page is followed to the product detail page, where the price (and the rest of the product data) is scraped
- active - indicates whether this distributor will be used in the searches
- probe_query - search term used by the health probes to test the distributor's selectors; falls back to the default probe query if omitted

## Distributor health monitoring

Every search records per-distributor statistics in `DistributorStats`: attempts, successes, success rate, average response time, and consecutive failures. From these the health status of each distributor is derived — `unknown`, `failing`, `degraded`, or `healthy` — and displayed in the Django admin, which also offers per-row actions to probe, activate, deactivate, or reset the statistics of selected distributors. A run of `DISTRIBUTOR_FAILURE_THRESHOLD` (default 5) consecutive failures automatically deactivates the distributor and flags it as disabled by the monitor, so a broken site does not slow down every search.

To keep the health status current even without user searches, the Celery beat schedule runs the `probe_distributors` task every 6 hours: it re-checks the active distributors' selectors using their `probe_query` (or `PROBE_DEFAULT_QUERY` from the environment) and records the outcome in the same statistics.

## Keeping the distributor list in sync

`search/fixtures/distributors.json` is the canonical, version-controlled list of distributors. The `sync_distributors` management command updates the database to match it:

```
python manage.py sync_distributors                   # dry run: prints the planned changes only
python manage.py sync_distributors --apply           # create and update rows to match the fixture
python manage.py sync_distributors --apply --prune   # also deactivate rows missing from the fixture
```

- Distributors are matched by `name`; their definition fields (`base_url`, `search_string`, `currency`, `included_vat`, the CSS selectors, `price_on_detail_page` and `probe_query`) are updated to match the fixture.
- Existing rows keep their `active` flag and their `DistributorStats` — manual activation/deactivation decisions and recorded statistics are never overwritten. Rows newly created by the sync take the `active` value from the fixture.
- `--prune` deactivates distributors missing from the fixture but never deletes them, so their statistics survive.
- After syncing, re-evaluate the health of the changed distributors from the Django admin (*Test now* action) or by running the `probe_distributors` task.

## Project Evolution / Next Steps

This is how the project evolved since the beginning:
- [x] Create a MVP using requests to get the HTML data and BeautifulSoup to parse it
- [x] Replace requests library with aiohttp to be able to load pages simultaneously/asynchronously
- [x] Use TailwindCSS to improve templates aesthetics
- [x] Experiment with using MongoDB Atlas instead of SQLite (using Djongo/PyMongo)
- [x] Drop aiohttp and use Playwright to be able to also get the dynamic content many pages have
- [x] Add lazy-load caching of pages using Redis
- [x] Migrate to PostreSQL for main database (using psycopg 3 driver)
- [x] Experiment with using Playwright also as parser instead of BeautifulSoup
- [x] Refactor html page parsing for decoupling from the concrete parser library and keep BeautifulSoup as default parser
- [x] Adjust project dependencies for deployment in Railway.app
- [x] Add Github Actions workflow

And these are the currently planned steps in its development:
- [x] Dockerize the project
- [x] Add intermediate "Loading" page for better user experience
- [x] Replace the "Loading" page with dynamic search results loading using Django Channels
- [x] Keep statistic of the top 100 most used search queries and use Celery to keep them up-to-date in cache
- [x] Reorganize the codebase into a services package with dedicated unit tests
- [x] Manage the Playwright browser lifecycle through a shared browser service
- [x] Monitor distributor health (recorded statistics, scheduled probes, Django admin UI)
- [x] Keep the distributor list in sync with the versioned fixture via the `sync_distributors` command
- [x] Productionize the Docker and Railway deployment


## Further Reading

- Playwright Documentation: https://playwright.dev/python/docs/intro
- BeautifulSoup Documentation: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- How to Use CSS Selectors: https://www.w3schools.com/cssref/css_selectors.php
- Using Caching in Django: https://docs.djangoproject.com/en/5.2/topics/cache/#basic-usage

## License

Composearch is released under the [MIT License](/LICENSE). Feel free to use, modify, and distribute the code as per the terms.
