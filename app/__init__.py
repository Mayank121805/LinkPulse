from flask import Flask, render_template, session, jsonify
from app.config import Config
from app.extensions import db, limiter, csrf
from app.models.user import User

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)

    # Register Blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.public import public_bp
    from app.blueprints.redirect import redirect_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.api import api_bp
    from app.blueprints.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(redirect_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    # Context Processors for Templates
    @app.context_processor
    def inject_globals():
        from app.utils.helpers import get_effective_base_url
        user = None
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
            
        return {
            'current_user': user,
            'base_url': get_effective_base_url()
        }

    # Error handlers
    @app.errorhandler(404)
    def handle_404(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def handle_500(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(429)
    def handle_429(e):
        return jsonify({
            'success': False,
            'message': 'Rate limit exceeded. Please wait a moment before trying again.'
        }), 429

    # Automatically create tables if not present
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            app.logger.error(f"Error initializing database tables: {e}")

    return app
