from flask import Blueprint
from app.extensions import csrf

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
csrf.exempt(admin_bp)

from app.blueprints.admin import routes
