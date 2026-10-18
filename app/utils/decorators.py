from functools import wraps
from flask import session, redirect, url_for, request, jsonify
from app.models.user import User

def get_current_user():
    """Returns current authenticated User object or None."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            return redirect(url_for('auth.login', next=request.url))
        
        # Verify user still exists and is active
        user = get_current_user()
        if not user or not user.is_active:
            session.clear()
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Account is inactive or not found'}), 401
            return redirect(url_for('auth.login', next=request.url))
            
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            return redirect(url_for('auth.login', next=request.url))
            
        user = get_current_user()
        if not user or not user.is_active or not user.is_admin:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Admin privilege required'}), 403
            return redirect(url_for('dashboard.overview'))
            
        return f(*args, **kwargs)
    return decorated_function
