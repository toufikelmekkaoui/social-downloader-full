"""
wsgi.py
-------
WSGI entry point for production servers (Gunicorn, uWSGI, etc.).

Usage examples
──────────────
    # Development
    python wsgi.py

    # Production with Gunicorn (4 sync workers)
    gunicorn "wsgi:app" --workers 4 --bind 0.0.0.0:8000 --timeout 120

    # Production with Gunicorn + gevent (async, recommended for streaming)
    gunicorn "wsgi:app" --workers 2 --worker-class gevent \
        --bind 0.0.0.0:8000 --timeout 300 --keep-alive 5

    # With environment variables
    FLASK_ENV=production SECRET_KEY=supersecret gunicorn "wsgi:app" \
        --workers 4 --bind 0.0.0.0:8000 --timeout 300
"""

import os
from app.factory import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("FLASK_ENV", "development") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug, threaded=True)
