# Phone & Gadgets Store

A Flask-powered electronics storefront adapted from the reference catalogue architecture. Includes a customer storefront, product collections and detail pages, cart and saved products, WhatsApp ordering, and a private owner dashboard for catalogue and inventory management.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
export SECRET_KEY='replace-with-a-random-secret-at-least-32-characters'
export DATABASE_URL='sqlite:///electronics_store.db'
export COOKIE_SECURE=false
flask --app 'app:create_app()' db upgrade
flask --app 'app:create_app()' run
```

For Render, use `pip install -r requirements.txt` as the build command and `gunicorn 'app:create_app()'` as the start command. Set `APP_ENV=production`, `SECRET_KEY`, `DATABASE_URL` (PostgreSQL), and `COOKIE_SECURE=true`. Run database migrations with `flask --app 'app:create_app()' db upgrade`.

Visit `/health` for application/database readiness. Configure the store and owner using the `bootstrap-store` CLI command and the `STORE_*` environment variables described in `app/__init__.py`.

## Tests

Run `python -m pytest -q`.
