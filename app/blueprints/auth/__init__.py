from flask import Blueprint
from app.extensions import csrf

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
csrf.exempt(auth_bp)

from app.blueprints.auth import routes
