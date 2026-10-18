from flask import Blueprint
from app.extensions import csrf

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
# Exempt API endpoints from CSRF to allow seamless AJAX/Fetch with session authentication
csrf.exempt(api_bp)

from app.blueprints.api import routes
