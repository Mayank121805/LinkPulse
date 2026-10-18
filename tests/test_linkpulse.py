import pytest
from datetime import datetime, timedelta
from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models.user import User
from app.models.link import Link
from app.models.click_event import ClickEvent
from app.models.blocked_domain import BlockedDomain
from app.models.campaign import Campaign

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        
        # Create test users
        admin = User(username='testadmin', email='admin@test.com', role='admin', is_active=True)
        admin.set_password('adminpass123')
        
        user = User(username='testuser', email='user@test.com', role='user', is_active=True)
        user.set_password('userpass123')
        
        # Blocked domain
        blocked = BlockedDomain(domain='badphishing.com', reason='Malicious phishing test')
        
        db.session.add_all([admin, user, blocked])
        db.session.commit()
        
        yield app
        
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def login_client(client, email, password):
    return client.post('/auth/login', data={'identifier': email, 'password': password}, follow_redirects=True)

# ==================== 1. HEALTH CHECK ====================
def test_health_check(client):
    res = client.get('/health')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'ok'
    assert 'healthy' in data['database']

# ==================== 2. AUTHENTICATION ====================
def test_auth_login_success(client):
    res = login_client(client, 'user@test.com', 'userpass123')
    assert res.status_code == 200
    with client.session_transaction() as sess:
        assert 'user_id' in sess
        assert sess['username'] == 'testuser'

def test_auth_login_invalid(client):
    res = login_client(client, 'user@test.com', 'wrongpassword')
    with client.session_transaction() as sess:
        assert 'user_id' not in sess

def test_auth_register(client):
    res = client.post('/auth/register', data={
        'username': 'newuser',
        'email': 'new@test.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert res.status_code == 200
    with client.session_transaction() as sess:
        assert sess['username'] == 'newuser'
        assert sess['role'] == 'user' # Never admin by default

# ==================== 3. LINK CREATION & VALIDATION ====================
def test_create_link_valid(client, app):
    login_client(client, 'user@test.com', 'userpass123')
    
    res = client.post('/api/v1/links', json={
        'destination_url': 'https://github.com/explore',
        'custom_alias': 'gh-explore',
        'title': 'GitHub Explore'
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data['success'] is True
    assert data['link']['effective_code'] == 'gh-explore'
    assert 'qr_data_uri' in data

def test_create_link_invalid_url(client):
    login_client(client, 'user@test.com', 'userpass123')
    res = client.post('/api/v1/links', json={
        'destination_url': 'not_a_valid_url',
        'title': 'Invalid URL Test'
    })
    assert res.status_code == 400
    data = res.get_json()
    assert data['success'] is False

def test_create_link_blocked_domain(client):
    login_client(client, 'user@test.com', 'userpass123')
    res = client.post('/api/v1/links', json={
        'destination_url': 'https://badphishing.com/steal-login',
        'title': 'Blocked Domain Test'
    })
    assert res.status_code == 400
    data = res.get_json()
    assert 'blocked' in data['message'].lower()

def test_create_link_duplicate_alias(client):
    login_client(client, 'user@test.com', 'userpass123')
    # First link
    client.post('/api/v1/links', json={
        'destination_url': 'https://python.org',
        'custom_alias': 'python-rocks'
    })
    # Second link with same alias
    res = client.post('/api/v1/links', json={
        'destination_url': 'https://google.com',
        'custom_alias': 'python-rocks'
    })
    assert res.status_code == 400
    assert 'already in use' in res.get_json()['message']

# ==================== 4. REDIRECTION ENGINE & RULES ====================
def test_redirect_active_and_click_recording(client, app):
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        link = Link(
            user_id=user.id,
            short_code='active1',
            destination_url='https://example.com/target',
            is_active=True
        )
        db.session.add(link)
        db.session.commit()
        link_id = link.id

    # Open short link
    res = client.get('/r/active1', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    assert res.status_code == 302
    assert res.location == 'https://example.com/target'

    # Verify click was recorded
    with app.app_context():
        l = Link.query.get(link_id)
        assert l.clicks_count == 1
        clicks = ClickEvent.query.filter_by(link_id=link_id).all()
        assert len(clicks) == 1
        assert clicks[0].device_category == 'desktop'

def test_redirect_disabled_link(client, app):
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        link = Link(user_id=user.id, short_code='dis1', destination_url='https://example.com', is_active=False)
        db.session.add(link)
        db.session.commit()

    res = client.get('/r/dis1')
    assert res.status_code == 403
    assert b'Link Disabled' in res.data

def test_redirect_expired_link(client, app):
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        link = Link(
            user_id=user.id,
            short_code='exp1',
            destination_url='https://example.com',
            expires_at=datetime.utcnow() - timedelta(days=2)
        )
        db.session.add(link)
        db.session.commit()

    res = client.get('/r/exp1')
    assert res.status_code == 410
    assert b'Link Expired' in res.data

def test_redirect_click_limit_reached(client, app):
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        link = Link(
            user_id=user.id,
            short_code='lim1',
            destination_url='https://example.com',
            max_clicks=5,
            clicks_count=5
        )
        db.session.add(link)
        db.session.commit()

    res = client.get('/r/lim1')
    assert res.status_code == 429
    assert b'Click Cap Exhausted' in res.data

def test_redirect_password_protection(client, app):
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        link = Link(user_id=user.id, short_code='sec1', destination_url='https://secretcompany.com')
        link.set_password('mypass123')
        db.session.add(link)
        db.session.commit()

    # GET without password shows prompt, does not redirect or leak destination
    res = client.get('/r/sec1')
    assert res.status_code == 200
    assert b'Password Protected Link' in res.data
    assert b'secretcompany.com' not in res.data

    # POST with wrong password
    res = client.post('/r/sec1', data={'password': 'wrong'})
    assert res.status_code == 401
    assert b'Incorrect password' in res.data

    # POST with correct password
    res = client.post('/r/sec1', data={'password': 'mypass123'})
    assert res.status_code == 302
    assert res.location == 'https://secretcompany.com'

# ==================== 5. ADMIN & GOVERNANCE ====================
def test_admin_authorization(client):
    # Regular user trying to access admin
    login_client(client, 'user@test.com', 'userpass123')
    res = client.get('/admin')
    assert res.status_code == 302 # Redirected away to dashboard

    # Admin accessing admin
    client.get('/auth/logout')
    login_client(client, 'admin@test.com', 'adminpass123')
    res = client.get('/admin')
    assert res.status_code == 200

# ==================== 6. QR CODE GENERATION ====================
def test_qr_code_generation(client, app):
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        link = Link(user_id=user.id, short_code='qrtest1', destination_url='https://example.com')
        db.session.add(link)
        db.session.commit()
        lid = link.id

    res = client.get(f'/api/v1/links/{lid}/qr')
    assert res.status_code == 200
    assert res.mimetype == 'image/png'
    assert len(res.data) > 100

# ==================== 7. CSV BULK IMPORT ====================
def test_csv_import_validation(client, app):
    login_client(client, 'user@test.com', 'userpass123')
    
    import io
    csv_content = (
        "destination_url,custom_alias,title,campaign\n"
        "https://valid1.com,csv-val-1,Valid One,Test Campaign\n"
        "invalid_url_row,csv-val-2,Invalid Row,Test Campaign\n"
        "https://valid2.com,,Valid Two,\n"
    )
    
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'test_import.csv')
    }
    
    res = client.post('/api/v1/import/csv', data=data, content_type='multipart/form-data')
    assert res.status_code == 200
    results = res.get_json()['results']
    assert results['total_rows'] == 3
    assert results['valid_count'] == 2
    assert results['error_count'] == 1
    assert results['errors'][0]['row'] == 3
