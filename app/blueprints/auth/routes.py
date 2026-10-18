import re
from urllib.parse import urlparse
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app.extensions import db, limiter
from app.models.user import User
from app.blueprints.auth import auth_bp

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_-]{3,30}$')

def is_safe_redirect_url(target):
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc or not test_url.netloc

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("20 per minute")
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard.overview'))

    next_url = request.args.get('next', '')
    
    if request.method == 'POST':
        # Accept form or JSON
        data = request.get_json() if request.is_json else request.form
        identifier = (data.get('identifier') or data.get('email') or '').strip()
        password = data.get('password', '')

        if not identifier or not password:
            msg = 'Please enter both your email/username and password.'
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 400
            flash(msg, 'error')
            return render_template('auth/login.html', identifier=identifier, next=next_url)

        # Lookup user by email or username
        user = User.query.filter(
            (User.email == identifier.lower()) | (User.username == identifier)
        ).first()

        if not user or not user.check_password(password):
            msg = 'Invalid credentials. Please verify your email/username and password.'
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 401
            flash(msg, 'error')
            return render_template('auth/login.html', identifier=identifier, next=next_url)

        if not user.is_active:
            msg = 'Your account has been deactivated. Please contact support.'
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 403
            flash(msg, 'error')
            return render_template('auth/login.html', identifier=identifier, next=next_url)

        # Establish session
        session.clear()
        session['user_id'] = user.id
        session['username'] = user.username
        session['email'] = user.email
        session['role'] = user.role
        session.permanent = True

        redirect_target = next_url if is_safe_redirect_url(next_url) else url_for('dashboard.overview')

        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': user.to_dict(),
                'redirect_url': redirect_target
            })

        return redirect(redirect_target)

    return render_template('auth/login.html', next=next_url)

@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard.overview'))

    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = (data.get('username') or '').strip()
        email = (data.get('email') or '').strip().lower()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')

        # Server-side validations
        if not username or not USERNAME_REGEX.match(username):
            msg = 'Username must be 3-30 characters with letters, numbers, hyphens, or underscores only.'
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 400
            flash(msg, 'error')
            return render_template('auth/register.html', username=username, email=email)

        if not email or not EMAIL_REGEX.match(email):
            msg = 'Please enter a valid email address.'
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 400
            flash(msg, 'error')
            return render_template('auth/register.html', username=username, email=email)

        if not password or len(password) < 6:
            msg = 'Password must be at least 6 characters long.'
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 400
            flash(msg, 'error')
            return render_template('auth/register.html', username=username, email=email)

        if confirm_password and password != confirm_password:
            msg = 'Passwords do not match.'
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 400
            flash(msg, 'error')
            return render_template('auth/register.html', username=username, email=email)

        # Check existing user
        if User.query.filter_by(username=username).first():
            msg = f"Username '{username}' is already taken."
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 400
            flash(msg, 'error')
            return render_template('auth/register.html', username=username, email=email)

        if User.query.filter_by(email=email).first():
            msg = f"Email '{email}' is already registered. Please sign in instead."
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 400
            flash(msg, 'error')
            return render_template('auth/register.html', username=username, email=email)

        # Create user (role always forced to 'user' on public registration for safety)
        new_user = User(
            username=username,
            email=email,
            role='user',
            is_active=True
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        # Log user in directly
        session.clear()
        session['user_id'] = new_user.id
        session['username'] = new_user.username
        session['email'] = new_user.email
        session['role'] = new_user.role
        session.permanent = True

        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Account created successfully',
                'user': new_user.to_dict(),
                'redirect_url': url_for('dashboard.overview')
            })

        flash('Welcome to LinkPulse! Your account has been created.', 'success')
        return redirect(url_for('dashboard.overview'))

    return render_template('auth/register.html')

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('public.landing'))
