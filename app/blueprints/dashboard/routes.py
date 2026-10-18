from flask import render_template, request, session, redirect, url_for, current_app, abort
from app.utils.decorators import login_required, get_current_user
from app.utils.helpers import get_effective_base_url
from app.models.link import Link
from app.models.campaign import Campaign
from app.models.tag import Tag
from app.blueprints.dashboard import dashboard_bp

@dashboard_bp.route('/dashboard')
@login_required
def overview():
    user = get_current_user()
    campaigns = Campaign.query.filter_by(user_id=user.id).all()
    base_url = get_effective_base_url()
    return render_template(
        'app/dashboard.html',
        user=user,
        campaigns=campaigns,
        base_url=base_url,
        active_nav='dashboard'
    )

@dashboard_bp.route('/links')
@login_required
def links():
    user = get_current_user()
    campaigns = Campaign.query.filter_by(user_id=user.id).all()
    tags = Tag.query.filter_by(user_id=user.id).all()
    base_url = get_effective_base_url()
    return render_template(
        'app/links.html',
        user=user,
        campaigns=campaigns,
        tags=tags,
        base_url=base_url,
        active_nav='links'
    )

@dashboard_bp.route('/links/<int:link_id>')
@login_required
def link_detail(link_id: int):
    user = get_current_user()
    link = Link.query.filter_by(id=link_id, user_id=user.id).first()
    if not link:
        # Admin can view any link detail
        if user.is_admin:
            link = Link.query.get_or_404(link_id)
        else:
            abort(404)

    base_url = get_effective_base_url()
    return render_template(
        'app/link_detail.html',
        user=user,
        link=link,
        base_url=base_url,
        active_nav='links'
    )

@dashboard_bp.route('/campaigns')
@login_required
def campaigns():
    user = get_current_user()
    user_campaigns = Campaign.query.filter_by(user_id=user.id).all()
    return render_template(
        'app/campaigns.html',
        user=user,
        campaigns=user_campaigns,
        active_nav='campaigns'
    )

@dashboard_bp.route('/qr-codes')
@login_required
def qr_codes():
    user = get_current_user()
    user_links = Link.query.filter_by(user_id=user.id).all()
    base_url = get_effective_base_url()
    return render_template(
        'app/qr_codes.html',
        user=user,
        links=user_links,
        base_url=base_url,
        active_nav='qr-codes'
    )

@dashboard_bp.route('/import')
@login_required
def bulk_import():
    user = get_current_user()
    return render_template(
        'app/bulk_import.html',
        user=user,
        active_nav='import'
    )

@dashboard_bp.route('/settings')
@login_required
def settings():
    user = get_current_user()
    base_url = get_effective_base_url()
    return render_template(
        'app/settings.html',
        user=user,
        base_url=base_url,
        active_nav='settings'
    )
