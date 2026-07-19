"""
extensions.py
-------------
Instantiate Flask extensions here (without an app object) so they can
be imported cleanly by both the factory and the individual blueprints.
"""

from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

cors = CORS()

limiter = Limiter(
    key_func=get_remote_address,
    # Default limits are applied per-route via decorators;
    # a global default is set from config inside create_app().
    default_limits=[],
)
