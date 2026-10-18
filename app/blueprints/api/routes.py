import io
from datetime import datetime
from flask import request, jsonify, current_app, Response, session
from sqlalchemy import or_, desc, asc
from app.extensions import db, limiter
from app.models.link import Link
from app.models.campaign import Campaign
from app.models.tag import Tag
from app.models.user import User
from app.utils.decorators import login_required, get_current_user
from app.services.link_service import (
    is_valid_url, validate_custom_alias, generate_short_code, get_or_create_tags
)
from app.services.analytics_service import get_dashboard_analytics, get_single_link_analytics
from app.services.qr_service import generate_qr_bytes, generate_qr_data_uri
from app.services.csv_service import parse_and_import_csv, get_sample_csv_content
from app.utils.helpers import get_effective_base_url
from app.blueprints.api import api_bp

# ==================== QUICK SHORTEN (LANDING PAGE) ====================

@api_bp.route('/links/quick-shorten', methods=['POST'])
@limiter.limit("30 per minute")
def quick_shorten():
    """Allows instant link creation from hero section on landing page."""
    data = request.get_json() or {}
    dest_url = (data.get('destination_url') or '').strip()
    custom_alias = (data.get('custom_alias') or '').strip()

    valid, err_msg = is_valid_url(dest_url)
    if not valid:
        return jsonify({'success': False, 'message': err_msg}), 400

    if custom_alias:
        valid_alias, alias_err = validate_custom_alias(custom_alias)
        if not valid_alias:
            return jsonify({'success': False, 'message': alias_err}), 400

    user_id = session.get('user_id')
    if not user_id:
        # If not logged in, assign to default demo user or create a temporary guest link
        demo_user = User.query.filter_by(role='admin').first() or User.query.first()
        user_id = demo_user.id if demo_user else 1

    short_code = generate_short_code()
    link = Link(
        user_id=user_id,
        short_code=short_code,
        custom_alias=custom_alias if custom_alias else None,
        destination_url=dest_url,
        title=dest_url
    )
    db.session.add(link)
    db.session.commit()

    base_url = get_effective_base_url()
    short_url = f"{base_url}/r/{link.effective_code}"
    qr_data_uri = generate_qr_data_uri(short_url)

    return jsonify({
        'success': True,
        'message': 'Link created successfully!',
        'link': link.to_dict(base_url),
        'qr_data_uri': qr_data_uri
    }), 201


# ==================== LINK MANAGEMENT ====================

@api_bp.route('/links', methods=['GET'])
@login_required
def list_links():
    """Lists links for current user with search, filtering, sorting and pagination."""
    user = get_current_user()
    base_url = get_effective_base_url()

    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'all')
    campaign_filter = request.args.get('campaign_id', '')
    tag_filter = request.args.get('tag_id', '')
    sort_by = request.args.get('sort_by', 'created_desc')
    
    try:
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(50, max(1, int(request.args.get('per_page', 10))))
    except ValueError:
        page = 1
        per_page = 10

    query = Link.query.filter_by(user_id=user.id)

    # Search filter
    if search:
        query = query.filter(or_(
            Link.title.ilike(f'%{search}%'),
            Link.destination_url.ilike(f'%{search}%'),
            Link.short_code.ilike(f'%{search}%'),
            Link.custom_alias.ilike(f'%{search}%')
        ))

    # Campaign filter
    if campaign_filter and campaign_filter.isdigit():
        query = query.filter(Link.campaign_id == int(campaign_filter))

    # Tag filter
    if tag_filter and tag_filter.isdigit():
        query = query.filter(Link.tags.any(Tag.id == int(tag_filter)))

    # Fetch all matching to evaluate dynamic status filters
    all_matching = query.all()

    # Dynamic status filtering
    now = datetime.utcnow()
    filtered_links = []
    for l in all_matching:
        if status_filter == 'active':
            if l.is_active and not (l.expires_at and l.expires_at < now) and not (l.max_clicks and l.clicks_count >= l.max_clicks):
                filtered_links.append(l)
        elif status_filter == 'disabled':
            if not l.is_active:
                filtered_links.append(l)
        elif status_filter == 'expired':
            if l.expires_at and l.expires_at < now:
                filtered_links.append(l)
        elif status_filter == 'limit_reached':
            if l.max_clicks and l.clicks_count >= l.max_clicks:
                filtered_links.append(l)
        else:
            filtered_links.append(l)

    # Sorting
    if sort_by == 'clicks_desc':
        filtered_links.sort(key=lambda x: x.clicks_count, reverse=True)
    elif sort_by == 'clicks_asc':
        filtered_links.sort(key=lambda x: x.clicks_count)
    elif sort_by == 'created_asc':
        filtered_links.sort(key=lambda x: x.created_at)
    else: # created_desc
        filtered_links.sort(key=lambda x: x.created_at, reverse=True)

    total_count = len(filtered_links)
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    start_idx = (page - 1) * per_page
    paginated_slice = filtered_links[start_idx:start_idx + per_page]

    return jsonify({
        'success': True,
        'links': [l.to_dict(base_url) for l in paginated_slice],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_count': total_count,
            'total_pages': total_pages
        }
    })

@api_bp.route('/links', methods=['POST'])
@login_required
@limiter.limit("60 per minute")
def create_link():
    """Two-step link creation wizard handler with full validation."""
    user = get_current_user()
    data = request.get_json() or {}

    dest_url = (data.get('destination_url') or '').strip()
    custom_alias = (data.get('custom_alias') or '').strip()
    title = (data.get('title') or '').strip()
    campaign_id = data.get('campaign_id')
    tags_input = data.get('tags') or []
    max_clicks = data.get('max_clicks')
    expires_at_str = data.get('expires_at')
    password = data.get('password')

    # 1. Validate destination URL
    valid, err_msg = is_valid_url(dest_url)
    if not valid:
        return jsonify({'success': False, 'message': err_msg}), 400

    # 2. Validate custom alias
    if custom_alias:
        valid_alias, alias_err = validate_custom_alias(custom_alias)
        if not valid_alias:
            return jsonify({'success': False, 'message': alias_err}), 400

    # 3. Validate Campaign
    validated_campaign_id = None
    if campaign_id:
        camp = Campaign.query.filter_by(id=campaign_id, user_id=user.id).first()
        if camp:
            validated_campaign_id = camp.id

    # 4. Validate Max Clicks
    validated_max_clicks = None
    if max_clicks is not None and str(max_clicks).strip() != '':
        try:
            val = int(max_clicks)
            if val <= 0:
                return jsonify({'success': False, 'message': 'Max clicks must be a positive number.'}), 400
            validated_max_clicks = val
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid max clicks value.'}), 400

    # 5. Validate Expiry Date
    validated_expiry = None
    if expires_at_str and str(expires_at_str).strip() != '':
        for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
            try:
                validated_expiry = datetime.strptime(expires_at_str.strip(), fmt)
                break
            except ValueError:
                pass
        if not validated_expiry:
            return jsonify({'success': False, 'message': 'Invalid expiry date format.'}), 400
        if validated_expiry <= datetime.utcnow():
            return jsonify({'success': False, 'message': 'Expiry date must be in the future.'}), 400

    # 6. Process Tags
    tag_names = []
    if isinstance(tags_input, list):
        tag_names = [str(t) for t in tags_input]
    elif isinstance(tags_input, str):
        tag_names = [t.strip() for t in tags_input.split(',') if t.strip()]
    tags = get_or_create_tags(user.id, tag_names)

    # 7. Generate collision-resistant code
    short_code = generate_short_code()

    # 8. Create Link
    new_link = Link(
        user_id=user.id,
        campaign_id=validated_campaign_id,
        short_code=short_code,
        custom_alias=custom_alias if custom_alias else None,
        destination_url=dest_url,
        title=title if title else dest_url,
        max_clicks=validated_max_clicks,
        expires_at=validated_expiry,
        tags=tags
    )
    if password and password.strip():
        new_link.set_password(password.strip())

    db.session.add(new_link)
    db.session.commit()

    base_url = get_effective_base_url()
    short_url = f"{base_url}/r/{new_link.effective_code}"
    qr_data_uri = generate_qr_data_uri(short_url)

    return jsonify({
        'success': True,
        'message': 'Link created successfully!',
        'link': new_link.to_dict(base_url),
        'qr_data_uri': qr_data_uri
    }), 201

@api_bp.route('/links/<int:link_id>', methods=['GET'])
@login_required
def get_link(link_id: int):
    """Fetches details for a single link."""
    user = get_current_user()
    link = Link.query.filter_by(id=link_id, user_id=user.id).first()
    if not link:
        if user.is_admin:
            link = Link.query.get_or_404(link_id)
        else:
            return jsonify({'success': False, 'message': 'Link not found or access denied'}), 404

    base_url = get_effective_base_url()
    short_url = f"{base_url}/r/{link.effective_code}"
    qr_data_uri = generate_qr_data_uri(short_url)

    data = link.to_dict(base_url)
    data['qr_data_uri'] = qr_data_uri
    return jsonify({'success': True, 'link': data})

@api_bp.route('/links/<int:link_id>', methods=['PUT'])
@login_required
def update_link(link_id: int):
    """Updates an existing link with ownership check."""
    user = get_current_user()
    link = Link.query.filter_by(id=link_id, user_id=user.id).first()
    if not link:
        if user.is_admin:
            link = Link.query.get_or_404(link_id)
        else:
            return jsonify({'success': False, 'message': 'Link not found or access denied'}), 404

    data = request.get_json() or {}
    dest_url = (data.get('destination_url') or '').strip()
    custom_alias = (data.get('custom_alias') or '').strip()
    title = (data.get('title') or '').strip()

    if dest_url:
        valid, err_msg = is_valid_url(dest_url)
        if not valid:
            return jsonify({'success': False, 'message': err_msg}), 400
        link.destination_url = dest_url

    if custom_alias != (link.custom_alias or ''):
        valid_alias, alias_err = validate_custom_alias(custom_alias, exclude_link_id=link.id)
        if not valid_alias:
            return jsonify({'success': False, 'message': alias_err}), 400
        link.custom_alias = custom_alias if custom_alias else None

    if title:
        link.title = title

    if 'campaign_id' in data:
        cid = data.get('campaign_id')
        if cid:
            camp = Campaign.query.filter_by(id=cid, user_id=user.id).first()
            link.campaign_id = camp.id if camp else None
        else:
            link.campaign_id = None

    if 'max_clicks' in data:
        max_clicks = data.get('max_clicks')
        if max_clicks is not None and str(max_clicks).strip() != '':
            try:
                link.max_clicks = int(max_clicks)
            except ValueError:
                pass
        else:
            link.max_clicks = None

    if 'expires_at' in data:
        exp_str = data.get('expires_at')
        if exp_str and str(exp_str).strip() != '':
            for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
                try:
                    link.expires_at = datetime.strptime(exp_str.strip(), fmt)
                    break
                except ValueError:
                    pass
        else:
            link.expires_at = None

    if 'password' in data:
        pwd = data.get('password')
        if pwd and pwd.strip():
            link.set_password(pwd.strip())
        elif pwd == "":
            link.password_hash = None

    if 'tags' in data:
        tags_input = data.get('tags') or []
        tag_names = [str(t) for t in tags_input] if isinstance(tags_input, list) else [t.strip() for t in tags_input.split(',') if t.strip()]
        link.tags = get_or_create_tags(user.id, tag_names)

    db.session.commit()
    base_url = get_effective_base_url()
    return jsonify({
        'success': True,
        'message': 'Link updated successfully',
        'link': link.to_dict(base_url)
    })

@api_bp.route('/links/<int:link_id>', methods=['DELETE'])
@login_required
def delete_link(link_id: int):
    """Deletes a link and all its click events."""
    user = get_current_user()
    link = Link.query.filter_by(id=link_id, user_id=user.id).first()
    if not link:
        if user.is_admin:
            link = Link.query.get_or_404(link_id)
        else:
            return jsonify({'success': False, 'message': 'Link not found or access denied'}), 404

    db.session.delete(link)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Link deleted successfully'})

@api_bp.route('/links/<int:link_id>/toggle', methods=['POST'])
@login_required
def toggle_link_status(link_id: int):
    """Toggles active status of a link."""
    user = get_current_user()
    link = Link.query.filter_by(id=link_id, user_id=user.id).first()
    if not link:
        if user.is_admin:
            link = Link.query.get_or_404(link_id)
        else:
            return jsonify({'success': False, 'message': 'Link not found or access denied'}), 404

    link.is_active = not link.is_active
    db.session.commit()

    action = "enabled" if link.is_active else "disabled"
    base_url = get_effective_base_url()
    return jsonify({
        'success': True,
        'message': f"Link {action} successfully",
        'is_active': link.is_active,
        'status': link.status,
        'link': link.to_dict(base_url)
    })

@api_bp.route('/links/<int:link_id>/qr', methods=['GET'])
def get_link_qr(link_id: int):
    """Generates QR code PNG for direct download or display."""
    link = Link.query.get_or_404(link_id)
    base_url = get_effective_base_url()
    short_url = f"{base_url}/r/{link.effective_code}"

    png_bytes = generate_qr_bytes(short_url, box_size=12)
    filename = f"linkpulse-qr-{link.effective_code}.png"

    response = Response(png_bytes, mimetype='image/png')
    if request.args.get('download') == 'true':
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ==================== CAMPAIGNS & TAGS ====================

@api_bp.route('/campaigns', methods=['GET'])
@login_required
def list_campaigns():
    user = get_current_user()
    campaigns = Campaign.query.filter_by(user_id=user.id).order_by(Campaign.created_at.desc()).all()
    return jsonify({
        'success': True,
        'campaigns': [c.to_dict(include_stats=True) for c in campaigns]
    })

@api_bp.route('/campaigns', methods=['POST'])
@login_required
def create_campaign():
    user = get_current_user()
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()
    color_code = (data.get('color_code') or '#2563EB').strip()

    if not name:
        return jsonify({'success': False, 'message': 'Campaign name is required'}), 400

    campaign = Campaign(
        user_id=user.id,
        name=name,
        description=description if description else None,
        color_code=color_code
    )
    db.session.add(campaign)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Campaign created successfully',
        'campaign': campaign.to_dict(include_stats=True)
    }), 201

@api_bp.route('/campaigns/<int:campaign_id>', methods=['PUT'])
@login_required
def update_campaign(campaign_id: int):
    user = get_current_user()
    campaign = Campaign.query.filter_by(id=campaign_id, user_id=user.id).first_or_404()
    data = request.get_json() or {}

    if 'name' in data and data['name'].strip():
        campaign.name = data['name'].strip()
    if 'description' in data:
        campaign.description = data['description'].strip()
    if 'color_code' in data:
        campaign.color_code = data['color_code'].strip()

    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Campaign updated successfully',
        'campaign': campaign.to_dict(include_stats=True)
    })

@api_bp.route('/campaigns/<int:campaign_id>', methods=['DELETE'])
@login_required
def delete_campaign(campaign_id: int):
    user = get_current_user()
    campaign = Campaign.query.filter_by(id=campaign_id, user_id=user.id).first_or_404()
    
    # Nullify links referencing this campaign before deletion
    Link.query.filter_by(campaign_id=campaign.id).update({Link.campaign_id: None})
    db.session.delete(campaign)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Campaign deleted successfully'})

@api_bp.route('/tags', methods=['GET'])
@login_required
def list_tags():
    user = get_current_user()
    tags = Tag.query.filter_by(user_id=user.id).all()
    return jsonify({
        'success': True,
        'tags': [t.to_dict() for t in tags]
    })


# ==================== ANALYTICS ====================

@api_bp.route('/analytics/overview', methods=['GET'])
@login_required
def analytics_overview():
    """Returns aggregated real-time dashboard analytics."""
    user = get_current_user()
    time_range = request.args.get('range', '7d')
    campaign_id = request.args.get('campaign_id')
    cid = int(campaign_id) if campaign_id and campaign_id.isdigit() else None

    # Calculate real analytics from database records
    analytics_data = get_dashboard_analytics(user_id=user.id, time_range=time_range, campaign_id=cid)
    return jsonify({'success': True, 'analytics': analytics_data})

@api_bp.route('/analytics/link/<int:link_id>', methods=['GET'])
@login_required
def analytics_single_link(link_id: int):
    """Returns analytics for an individual link."""
    user = get_current_user()
    link = Link.query.filter_by(id=link_id, user_id=user.id).first()
    if not link:
        if user.is_admin:
            link = Link.query.get_or_404(link_id)
        else:
            return jsonify({'success': False, 'message': 'Link not found'}), 404

    time_range = request.args.get('range', '30d')
    data = get_single_link_analytics(link, time_range=time_range)
    return jsonify({'success': True, 'analytics': data})


# ==================== CSV BULK IMPORT & SAMPLE ====================

@api_bp.route('/import/csv', methods=['POST'])
@login_required
def import_csv():
    """Handles CSV bulk upload, validating each row and returning row-level reports."""
    user = get_current_user()
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400

    file = request.files['file']
    if not file.filename or not file.filename.lower().endswith('.csv'):
        return jsonify({'success': False, 'message': 'Please upload a valid .csv file'}), 400

    results = parse_and_import_csv(file.stream, user.id)
    return jsonify({'success': True, 'results': results})

@api_bp.route('/sample-csv', methods=['GET'])
def download_sample_csv():
    """Generates and serves a sample CSV file for users."""
    content = get_sample_csv_content()
    return Response(
        content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=linkpulse-sample-import.csv"}
    )
