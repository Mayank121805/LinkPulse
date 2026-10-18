import csv
import io
from datetime import datetime
from app.extensions import db
from app.models.link import Link
from app.models.campaign import Campaign
from app.services.link_service import (
    is_valid_url, validate_custom_alias, generate_short_code, get_or_create_tags
)

REQUIRED_HEADERS = {'destination_url'}

def parse_and_import_csv(file_stream, user_id: int) -> dict:
    """
    Parses a CSV file stream, validates each row, and imports valid links.
    Returns a comprehensive validation report with row-level error reasons.
    """
    results = {
        'total_rows': 0,
        'valid_count': 0,
        'error_count': 0,
        'imported_links': [],
        'errors': []
    }

    try:
        # Read text content safely
        content = file_stream.read()
        if isinstance(content, bytes):
            # Attempt UTF-8, then latin1
            try:
                content = content.decode('utf-8-sig')
            except UnicodeDecodeError:
                content = content.decode('latin1')

        # Detect dialect / delimiter
        sample = content[:4096]
        delimiter = ','
        if sample:
            try:
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample)
                delimiter = dialect.delimiter
            except Exception:
                delimiter = ','

        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        
        # Check header
        if not reader.fieldnames:
            results['errors'].append({'row': 0, 'reason': 'The uploaded CSV file is empty.'})
            return results

        # Normalize fieldnames (lowercase, stripped)
        fieldnames_normalized = {f.strip().lower(): f for f in reader.fieldnames if f}
        if 'destination_url' not in fieldnames_normalized:
            results['errors'].append({
                'row': 1,
                'reason': f"Missing required column 'destination_url'. Found headers: {list(reader.fieldnames)}"
            })
            return results

        url_key = fieldnames_normalized['destination_url']
        alias_key = fieldnames_normalized.get('custom_alias', None)
        title_key = fieldnames_normalized.get('title', None)
        camp_key = fieldnames_normalized.get('campaign', fieldnames_normalized.get('campaign_name', None))
        tags_key = fieldnames_normalized.get('tags', None)
        max_clicks_key = fieldnames_normalized.get('max_clicks', None)
        expires_key = fieldnames_normalized.get('expires_at', fieldnames_normalized.get('expiry_date', None))

        created_in_batch_aliases = set()

        for idx, row in enumerate(reader, start=2): # Start at 2 accounting for header
            results['total_rows'] += 1
            dest_url = (row.get(url_key) or '').strip()
            alias = (row.get(alias_key) or '').strip() if alias_key else ''
            title = (row.get(title_key) or '').strip() if title_key else ''
            camp_name = (row.get(camp_key) or '').strip() if camp_key else ''
            tags_str = (row.get(tags_key) or '').strip() if tags_key else ''
            max_clicks_str = (row.get(max_clicks_key) or '').strip() if max_clicks_key else ''
            expires_str = (row.get(expires_key) or '').strip() if expires_key else ''

            # 1. Validate Destination URL
            valid_url, url_err = is_valid_url(dest_url)
            if not valid_url:
                results['error_count'] += 1
                results['errors'].append({'row': idx, 'url': dest_url, 'reason': url_err})
                continue

            # 2. Validate Custom Alias
            if alias:
                if alias.lower() in created_in_batch_aliases:
                    results['error_count'] += 1
                    results['errors'].append({'row': idx, 'url': dest_url, 'reason': f"Duplicate alias '{alias}' within the same CSV."})
                    continue
                valid_alias, alias_err = validate_custom_alias(alias)
                if not valid_alias:
                    results['error_count'] += 1
                    results['errors'].append({'row': idx, 'url': dest_url, 'reason': alias_err})
                    continue

            # 3. Validate max_clicks
            max_clicks = None
            if max_clicks_str:
                try:
                    max_clicks = int(max_clicks_str)
                    if max_clicks <= 0:
                        results['error_count'] += 1
                        results['errors'].append({'row': idx, 'url': dest_url, 'reason': 'max_clicks must be a positive integer.'})
                        continue
                except ValueError:
                    results['error_count'] += 1
                    results['errors'].append({'row': idx, 'url': dest_url, 'reason': 'max_clicks must be a valid number.'})
                    continue

            # 4. Validate expires_at
            expires_at = None
            if expires_str:
                for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M'):
                    try:
                        expires_at = datetime.strptime(expires_str, fmt)
                        break
                    except ValueError:
                        pass
                if not expires_at:
                    results['error_count'] += 1
                    results['errors'].append({'row': idx, 'url': dest_url, 'reason': f"Invalid date format '{expires_str}'. Use YYYY-MM-DD or YYYY-MM-DD HH:MM."})
                    continue
                if expires_at <= datetime.utcnow():
                    results['error_count'] += 1
                    results['errors'].append({'row': idx, 'url': dest_url, 'reason': 'Expiry date must be in the future.'})
                    continue

            # 5. Handle Campaign
            campaign_id = None
            if camp_name:
                camp = Campaign.query.filter_by(user_id=user_id, name=camp_name).first()
                if not camp:
                    camp = Campaign(user_id=user_id, name=camp_name, description=f"Imported via CSV on {datetime.utcnow().strftime('%Y-%m-%d')}")
                    db.session.add(camp)
                    db.session.flush()
                campaign_id = camp.id

            # 6. Handle Tags
            tags = []
            if tags_str:
                tag_names = [t.strip() for t in tags_str.split(',') if t.strip()]
                tags = get_or_create_tags(user_id, tag_names)

            # Generate Short Code
            short_code = generate_short_code()

            # Create Link
            new_link = Link(
                user_id=user_id,
                campaign_id=campaign_id,
                short_code=short_code,
                custom_alias=alias if alias else None,
                destination_url=dest_url,
                title=title if title else dest_url,
                max_clicks=max_clicks,
                expires_at=expires_at,
                tags=tags
            )
            
            db.session.add(new_link)
            if alias:
                created_in_batch_aliases.add(alias.lower())

            results['valid_count'] += 1
            results['imported_links'].append({
                'row': idx,
                'short_code': alias if alias else short_code,
                'destination_url': dest_url,
                'title': title or dest_url,
                'campaign': camp_name or 'None'
            })

        # Commit all valid links in transaction
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        results['errors'].append({'row': 0, 'reason': f"CSV processing error: {str(e)}"})

    return results

def get_sample_csv_content() -> str:
    """Returns a sample CSV formatted string for user download."""
    rows = [
        ['destination_url', 'custom_alias', 'title', 'campaign', 'tags', 'max_clicks', 'expires_at'],
        ['https://github.com/trending', 'gh-trends', 'GitHub Trending Repos', 'Developer Outreach', 'github,tech,dev', '500', '2026-12-31 23:59:59'],
        ['https://news.ycombinator.com', 'hn-front', 'Hacker News Frontpage', 'Tech News', 'hacker-news,startup', '', ''],
        ['https://python.org', 'py-official', 'Official Python Portal', 'Developer Outreach', 'python,programming', '1000', '2026-11-30 18:00:00'],
        ['https://chartjs.org/docs', '', 'Chart.js Documentation', 'Design Assets', 'docs,charts', '', '']
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(rows)
    return output.getvalue()
