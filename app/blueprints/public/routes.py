from datetime import datetime
from flask import render_template, jsonify, current_app, session
from app.extensions import db
from app.models.link import Link
from app.models.click_event import ClickEvent
from app.models.user import User
from app.blueprints.public import public_bp

@public_bp.route('/')
def landing():
    # Pass platform summary metrics for social proof on landing page
    total_clicks = db.session.query(db.func.count(ClickEvent.id)).scalar() or 0
    total_links = db.session.query(db.func.count(Link.id)).scalar() or 0
    
    return render_template(
        'landing.html',
        total_clicks=total_clicks,
        total_links=total_links,
        is_logged_in='user_id' in session
    )

@public_bp.route('/health')
def health_check():
    """Application and database health check endpoint."""
    db_status = "healthy"
    try:
        db.session.execute(db.text('SELECT 1'))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return jsonify({
        'status': 'ok' if db_status == 'healthy' else 'degraded',
        'database': db_status,
        'timestamp': datetime.utcnow().isoformat(),
        'platform': 'LinkPulse Enterprise URL Shortener & Analytics',
        'version': '1.0.0'
    }), (200 if db_status == 'healthy' else 503)
