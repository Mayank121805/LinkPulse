from datetime import datetime, timedelta
from sqlalchemy import func, distinct, desc
from app.extensions import db
from app.models.link import Link
from app.models.click_event import ClickEvent
from app.models.campaign import Campaign

def get_date_filter_range(time_range: str):
    """Calculates start datetime based on requested range."""
    now = datetime.utcnow()
    if time_range == '24h':
        return now - timedelta(hours=24)
    elif time_range == '7d':
        return now - timedelta(days=7)
    elif time_range == '30d':
        return now - timedelta(days=30)
    elif time_range == '90d':
        return now - timedelta(days=90)
    return None # 'all'

def get_dashboard_analytics(user_id: int = None, time_range: str = '7d', campaign_id: int = None):
    """
    Computes comprehensive analytics across all links owned by a user
    (or platform-wide if user_id is None).
    """
    # 1. Base Link Query
    link_query = Link.query
    if user_id is not None:
        link_query = link_query.filter(Link.user_id == user_id)
    if campaign_id is not None:
        link_query = link_query.filter(Link.campaign_id == campaign_id)

    all_links = link_query.all()
    total_links = len(all_links)
    active_links = sum(1 for l in all_links if l.status == 'active')
    disabled_or_expired = sum(1 for l in all_links if l.status in ('disabled', 'expired', 'limit_reached'))
    link_ids = [l.id for l in all_links]

    if not link_ids:
        return _empty_analytics_response(total_links, active_links, disabled_or_expired)

    # 2. Base Click Query
    click_query = ClickEvent.query.filter(ClickEvent.link_id.in_(link_ids))
    start_date = get_date_filter_range(time_range)
    if start_date:
        click_query = click_query.filter(ClickEvent.timestamp >= start_date)

    # 3. Aggregates & KPIs
    total_clicks = click_query.count()
    unique_visitors = db.session.query(func.count(distinct(ClickEvent.visitor_hash)))\
        .filter(ClickEvent.link_id.in_(link_ids))\
        .filter(ClickEvent.timestamp >= start_date if start_date else True)\
        .scalar() or 0

    bot_clicks = click_query.filter(ClickEvent.is_bot == True).count()

    # 4. Clicks Over Time (Trend)
    clicks_over_time = _get_clicks_over_time(link_ids, start_date, time_range)

    # 5. Device Distribution
    device_data = db.session.query(
        ClickEvent.device_category, func.count(ClickEvent.id)
    ).filter(ClickEvent.link_id.in_(link_ids))\
     .filter(ClickEvent.timestamp >= start_date if start_date else True)\
     .group_by(ClickEvent.device_category).all()
    
    device_breakdown = {cat: 0 for cat in ['desktop', 'mobile', 'tablet', 'bot']}
    for cat, count in device_data:
        device_breakdown[cat] = count

    # 6. Browser Distribution
    browser_data = db.session.query(
        ClickEvent.browser, func.count(ClickEvent.id)
    ).filter(ClickEvent.link_id.in_(link_ids))\
     .filter(ClickEvent.timestamp >= start_date if start_date else True)\
     .group_by(ClickEvent.browser)\
     .order_by(desc(func.count(ClickEvent.id))).limit(6).all()
    
    browser_breakdown = [{'label': b or 'Unknown', 'count': c} for b, c in browser_data]

    # 7. Traffic Sources / Referrers
    referrer_data = db.session.query(
        ClickEvent.referrer_domain, func.count(ClickEvent.id)
    ).filter(ClickEvent.link_id.in_(link_ids))\
     .filter(ClickEvent.timestamp >= start_date if start_date else True)\
     .group_by(ClickEvent.referrer_domain)\
     .order_by(desc(func.count(ClickEvent.id))).limit(7).all()
    
    referrer_breakdown = [{'source': r or 'Direct', 'count': c} for r, c in referrer_data]

    # 8. Campaign Performance
    campaign_performance = []
    user_campaigns_query = Campaign.query
    if user_id is not None:
        user_campaigns_query = user_campaigns_query.filter(Campaign.user_id == user_id)
    user_campaigns = user_campaigns_query.all()
    
    for c in user_campaigns:
        c_links = [l for l in all_links if l.campaign_id == c.id]
        c_clicks = sum(l.clicks_count for l in c_links)
        campaign_performance.append({
            'id': c.id,
            'name': c.name,
            'color': c.color_code,
            'links_count': len(c_links),
            'total_clicks': c_clicks
        })

    # Sort campaigns by clicks descending
    campaign_performance.sort(key=lambda x: x['total_clicks'], reverse=True)

    # 9. Top Performing Links
    top_links_query = sorted(all_links, key=lambda l: l.clicks_count, reverse=True)[:5]
    top_links = [l.to_dict() for l in top_links_query]

    # 10. Recent Activity Log
    recent_events_raw = ClickEvent.query.filter(ClickEvent.link_id.in_(link_ids))\
        .order_by(ClickEvent.timestamp.desc()).limit(10).all()
    
    # Map links for quick lookup
    link_map = {l.id: l.effective_code for l in all_links}
    recent_activity = []
    for ev in recent_events_raw:
        item = ev.to_dict()
        item['short_code'] = link_map.get(ev.link_id, 'unknown')
        recent_activity.append(item)

    # 11. Expiring Link Alerts (expiring in next 7 days)
    now = datetime.utcnow()
    expiring_soon = [
        l.to_dict() for l in all_links 
        if l.expires_at and now < l.expires_at <= (now + timedelta(days=7)) and l.is_active
    ]

    return {
        'kpis': {
            'total_clicks': total_clicks,
            'unique_visitors': unique_visitors,
            'total_links': total_links,
            'active_links': active_links,
            'disabled_or_expired': disabled_or_expired,
            'bot_clicks': bot_clicks
        },
        'clicks_over_time': clicks_over_time,
        'device_breakdown': device_breakdown,
        'browser_breakdown': browser_breakdown,
        'referrer_breakdown': referrer_breakdown,
        'campaign_performance': campaign_performance,
        'top_links': top_links,
        'recent_activity': recent_activity,
        'expiring_alerts': expiring_soon
    }

def get_single_link_analytics(link: Link, time_range: str = '30d'):
    """Detailed analytics breakdown for a single link."""
    start_date = get_date_filter_range(time_range)
    query = ClickEvent.query.filter(ClickEvent.link_id == link.id)
    if start_date:
        query = query.filter(ClickEvent.timestamp >= start_date)

    total_clicks = query.count()
    unique_visitors = db.session.query(func.count(distinct(ClickEvent.visitor_hash)))\
        .filter(ClickEvent.link_id == link.id)\
        .filter(ClickEvent.timestamp >= start_date if start_date else True)\
        .scalar() or 0

    clicks_over_time = _get_clicks_over_time([link.id], start_date, time_range)

    # Devices
    device_data = db.session.query(
        ClickEvent.device_category, func.count(ClickEvent.id)
    ).filter(ClickEvent.link_id == link.id)\
     .filter(ClickEvent.timestamp >= start_date if start_date else True)\
     .group_by(ClickEvent.device_category).all()
    
    device_breakdown = {cat: 0 for cat in ['desktop', 'mobile', 'tablet', 'bot']}
    for cat, count in device_data:
        device_breakdown[cat] = count

    # Browsers
    browser_data = db.session.query(
        ClickEvent.browser, func.count(ClickEvent.id)
    ).filter(ClickEvent.link_id == link.id)\
     .filter(ClickEvent.timestamp >= start_date if start_date else True)\
     .group_by(ClickEvent.browser)\
     .order_by(desc(func.count(ClickEvent.id))).limit(6).all()
    browser_breakdown = [{'label': b or 'Unknown', 'count': c} for b, c in browser_data]

    # Referrers
    referrer_data = db.session.query(
        ClickEvent.referrer_domain, func.count(ClickEvent.id)
    ).filter(ClickEvent.link_id == link.id)\
     .filter(ClickEvent.timestamp >= start_date if start_date else True)\
     .group_by(ClickEvent.referrer_domain)\
     .order_by(desc(func.count(ClickEvent.id))).limit(7).all()
    referrer_breakdown = [{'source': r or 'Direct', 'count': c} for r, c in referrer_data]

    # Recent clicks
    recent_clicks = [ev.to_dict() for ev in query.order_by(ClickEvent.timestamp.desc()).limit(20).all()]

    return {
        'link': link.to_dict(),
        'kpis': {
            'total_clicks': total_clicks,
            'unique_visitors': unique_visitors,
            'lifetime_clicks': link.clicks_count
        },
        'clicks_over_time': clicks_over_time,
        'device_breakdown': device_breakdown,
        'browser_breakdown': browser_breakdown,
        'referrer_breakdown': referrer_breakdown,
        'recent_clicks': recent_clicks
    }

def _get_clicks_over_time(link_ids: list[int], start_date: datetime, time_range: str):
    """Generates continuous timeline data points for Chart.js."""
    now = datetime.utcnow()
    labels = []
    points = {}

    if time_range == '24h':
        # Hour by hour
        for i in range(24):
            dt = now - timedelta(hours=23 - i)
            key = dt.strftime('%H:00')
            labels.append(key)
            points[key] = 0

        events = ClickEvent.query.filter(
            ClickEvent.link_id.in_(link_ids),
            ClickEvent.timestamp >= (now - timedelta(hours=24))
        ).all()
        for ev in events:
            hour_key = ev.timestamp.strftime('%H:00')
            if hour_key in points:
                points[hour_key] += 1
    else:
        # Day by day
        num_days = 7 if time_range == '7d' else (30 if time_range == '30d' else 14)
        for i in range(num_days):
            dt = (now - timedelta(days=num_days - 1 - i)).date()
            key = dt.strftime('%b %d')
            labels.append(key)
            points[key] = 0

        effective_start = now - timedelta(days=num_days)
        events = ClickEvent.query.filter(
            ClickEvent.link_id.in_(link_ids),
            ClickEvent.timestamp >= effective_start
        ).all()
        for ev in events:
            day_key = ev.timestamp.strftime('%b %d')
            if day_key in points:
                points[day_key] += 1

    return {
        'labels': labels,
        'data': [points[lbl] for lbl in labels]
    }

def _empty_analytics_response(total_links, active_links, disabled_or_expired):
    now = datetime.utcnow()
    labels = [(now - timedelta(days=6 - i)).strftime('%b %d') for i in range(7)]
    return {
        'kpis': {
            'total_clicks': 0,
            'unique_visitors': 0,
            'total_links': total_links,
            'active_links': active_links,
            'disabled_or_expired': disabled_or_expired,
            'bot_clicks': 0
        },
        'clicks_over_time': {'labels': labels, 'data': [0] * 7},
        'device_breakdown': {'desktop': 0, 'mobile': 0, 'tablet': 0, 'bot': 0},
        'browser_breakdown': [],
        'referrer_breakdown': [],
        'campaign_performance': [],
        'top_links': [],
        'recent_activity': [],
        'expiring_alerts': []
    }
