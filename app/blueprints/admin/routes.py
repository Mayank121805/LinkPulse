from datetime import datetime
from flask import render_template, request, jsonify, current_app
from sqlalchemy import or_, desc, func
from app.extensions import db
from app.models.user import User
from app.models.link import Link
from app.models.click_event import ClickEvent
from app.models.blocked_domain import BlockedDomain
from app.models.admin_log import AdminLog
from app.utils.decorators import admin_required, get_current_user
from app.utils.helpers import get_effective_base_url
from app.services.analytics_service import get_dashboard_analytics
from app.blueprints.admin import admin_bp

@admin_bp.route('')
@admin_bp.route('/')
@admin_required
def admin_dashboard():
    user = get_current_user()
    base_url = get_effective_base_url()
    return render_template(
        'admin/dashboard.html',
        user=user,
        base_url=base_url,
        active_nav='admin'
    )

@admin_bp.route('/api/stats', methods=['GET'])
@admin_required
def get_admin_stats():
    """Platform-wide system metrics for administrators."""
    total_users = User.query.count()
    total_links = Link.query.count()
    total_clicks = ClickEvent.query.count()
    blocked_domains_count = BlockedDomain.query.count()
    bot_clicks = ClickEvent.query.filter_by(is_bot=True).count()
    disabled_links = Link.query.filter_by(is_active=False).count()

    # Platform overview analytics
    analytics = get_dashboard_analytics(user_id=None, time_range='7d')

    return jsonify({
        'success': True,
        'stats': {
            'total_users': total_users,
            'total_links': total_links,
            'total_clicks': total_clicks,
            'blocked_domains': blocked_domains_count,
            'bot_clicks': bot_clicks,
            'disabled_links': disabled_links
        },
        'analytics': analytics
    })

@admin_bp.route('/api/users', methods=['GET'])
@admin_required
def get_all_users():
    """Returns list of all users with their link & click counts."""
    users = User.query.order_by(User.created_at.desc()).all()
    user_list = []
    for u in users:
        u_dict = u.to_dict()
        u_dict['links_count'] = u.links.count()
        u_dict['total_clicks'] = db.session.query(func.coalesce(func.sum(Link.clicks_count), 0))\
            .filter(Link.user_id == u.id).scalar()
        user_list.append(u_dict)

    return jsonify({'success': True, 'users': user_list})

@admin_bp.route('/api/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id: int):
    admin = get_current_user()
    target_user = User.query.get_or_404(user_id)

    if target_user.id == admin.id:
        return jsonify({'success': False, 'message': 'You cannot deactivate your own admin account.'}), 400

    target_user.is_active = not target_user.is_active
    
    # Audit log
    log = AdminLog(
        admin_user_id=admin.id,
        action='deactivate_user' if not target_user.is_active else 'activate_user',
        target_type='user',
        target_id=target_user.id,
        details=f"Admin {admin.username} toggled status of {target_user.username} to {target_user.is_active}"
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"User account {'activated' if target_user.is_active else 'deactivated'} successfully",
        'is_active': target_user.is_active
    })

@admin_bp.route('/api/users/<int:user_id>/toggle-role', methods=['POST'])
@admin_required
def toggle_user_role(user_id: int):
    admin = get_current_user()
    target_user = User.query.get_or_404(user_id)

    if target_user.id == admin.id:
        return jsonify({'success': False, 'message': 'You cannot change your own admin role.'}), 400

    target_user.role = 'user' if target_user.role == 'admin' else 'admin'
    
    log = AdminLog(
        admin_user_id=admin.id,
        action='change_role',
        target_type='user',
        target_id=target_user.id,
        details=f"Admin {admin.username} changed role of {target_user.username} to {target_user.role}"
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"User role changed to {target_user.role}",
        'role': target_user.role
    })

@admin_bp.route('/api/links', methods=['GET'])
@admin_required
def get_all_links():
    """Search and view all links across the entire platform."""
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'all')
    base_url = get_effective_base_url()

    query = Link.query
    if search:
        query = query.filter(or_(
            Link.title.ilike(f'%{search}%'),
            Link.destination_url.ilike(f'%{search}%'),
            Link.short_code.ilike(f'%{search}%'),
            Link.custom_alias.ilike(f'%{search}%')
        ))

    links = query.order_by(Link.created_at.desc()).limit(100).all()
    results = []
    for l in links:
        d = l.to_dict(base_url)
        d['owner_username'] = l.owner.username if l.owner else 'Unknown'
        results.append(d)

    return jsonify({'success': True, 'links': results})

@admin_bp.route('/api/links/<int:link_id>/takedown', methods=['POST'])
@admin_required
def takedown_link(link_id: int):
    """Allows an administrator to immediately disable or take down an abusive link."""
    admin = get_current_user()
    link = Link.query.get_or_404(link_id)
    
    data = request.get_json() or {}
    action = data.get('action', 'disable') # 'disable' or 'delete'

    if action == 'delete':
        db.session.delete(link)
        log = AdminLog(
            admin_user_id=admin.id,
            action='delete_link',
            target_type='link',
            target_id=link_id,
            details=f"Admin {admin.username} deleted link {link.effective_code} ({link.destination_url[:40]})"
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Link deleted permanently from platform.'})
    else:
        link.is_active = not link.is_active
        log = AdminLog(
            admin_user_id=admin.id,
            action='disable_link' if not link.is_active else 'enable_link',
            target_type='link',
            target_id=link.id,
            details=f"Admin {admin.username} changed status of link {link.effective_code} to {link.is_active}"
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f"Link {'enabled' if link.is_active else 'disabled'} successfully",
            'is_active': link.is_active
        })

@admin_bp.route('/api/blocked-domains', methods=['GET'])
@admin_required
def list_blocked_domains():
    domains = BlockedDomain.query.order_by(BlockedDomain.created_at.desc()).all()
    return jsonify({'success': True, 'blocked_domains': [d.to_dict() for d in domains]})

@admin_bp.route('/api/blocked-domains', methods=['POST'])
@admin_required
def add_blocked_domain():
    admin = get_current_user()
    data = request.get_json() or {}
    domain = (data.get('domain') or '').strip().lower()
    reason = (data.get('reason') or 'Malicious or abusive destination').strip()

    if not domain:
        return jsonify({'success': False, 'message': 'Domain is required'}), 400

    # Clean domain
    if '://' in domain:
        domain = domain.split('://')[1]
    domain = domain.split('/')[0].split(':')[0]
    if domain.startswith('www.'):
        domain = domain[4:]

    if BlockedDomain.query.filter_by(domain=domain).first():
        return jsonify({'success': False, 'message': f"Domain '{domain}' is already blocked"}), 400

    new_block = BlockedDomain(
        domain=domain,
        reason=reason,
        created_by_user_id=admin.id
    )
    db.session.add(new_block)

    # Disable any existing links targeting this domain
    affected = Link.query.filter(Link.destination_url.ilike(f'%{domain}%')).all()
    for l in affected:
        l.is_active = False

    log = AdminLog(
        admin_user_id=admin.id,
        action='block_domain',
        target_type='domain',
        details=f"Blocked domain '{domain}'. Disabled {len(affected)} associated links."
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"Domain '{domain}' blocked successfully. {len(affected)} active links were disabled.",
        'domain': new_block.to_dict()
    }), 201

@admin_bp.route('/api/blocked-domains/<int:domain_id>', methods=['DELETE'])
@admin_required
def delete_blocked_domain(domain_id: int):
    admin = get_current_user()
    domain_obj = BlockedDomain.query.get_or_404(domain_id)
    dom_name = domain_obj.domain

    db.session.delete(domain_obj)
    log = AdminLog(
        admin_user_id=admin.id,
        action='unblock_domain',
        target_type='domain',
        details=f"Unblocked domain '{dom_name}'"
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({'success': True, 'message': f"Domain '{dom_name}' unblocked successfully"})

@admin_bp.route('/api/logs', methods=['GET'])
@admin_required
def get_audit_logs():
    logs = AdminLog.query.order_by(AdminLog.created_at.desc()).limit(50).all()
    return jsonify({'success': True, 'logs': [l.to_dict() for l in logs]})
