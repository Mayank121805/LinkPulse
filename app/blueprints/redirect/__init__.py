from flask import Blueprint

redirect_bp = Blueprint('redirect_bp', __name__)

from app.blueprints.redirect import routes
