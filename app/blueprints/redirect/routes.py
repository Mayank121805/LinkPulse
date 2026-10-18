from flask import render_template, request, redirect, abort, current_app
from app.extensions import csrf
from app.services.redirect_service import resolve_and_evaluate_link
from app.blueprints.redirect import redirect_bp

@redirect_bp.route('/r/<path:code>', methods=['GET', 'POST'])
@csrf.exempt
def handle_redirect(code: str):
    """
    Public short-link entry point.
    Evaluates link rules, records click events, and handles password verification.
    """
    password = request.form.get('password') if request.method == 'POST' else None
    
    status, result = resolve_and_evaluate_link(code, request, password=password)

    if status == 'redirect':
        return redirect(result, code=302)

    elif status == 'password_required':
        return render_template('redirect/password_prompt.html', link=result, code=code, error=None), 200

    elif status == 'invalid_password':
        return render_template(
            'redirect/password_prompt.html',
            link=result,
            code=code,
            error='Incorrect password. Please try again.'
        ), 401

    elif status == 'disabled':
        return render_template('errors/disabled.html', link=result), 403

    elif status == 'expired':
        return render_template('errors/expired.html', link=result), 410

    elif status == 'limit_reached':
        return render_template('errors/limit_reached.html', link=result), 429

    elif status == 'not_found':
        return render_template('errors/404.html', code=code), 404

    return render_template('errors/404.html', code=code), 404
