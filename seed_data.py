import sys
import random
import hashlib
from datetime import datetime, timedelta, timezone
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.campaign import Campaign
from app.models.tag import Tag
from app.models.link import Link
from app.models.click_event import ClickEvent
from app.models.blocked_domain import BlockedDomain
from app.models.admin_log import AdminLog
from app.services.link_service import generate_short_code

def get_utc_now():
    """Returns naive UTC datetime compatible with MySQL & Python 3.14+."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def seed_database(reset=False):
    app = create_app()
    with app.app_context():
        print("Initializing database tables...")
        db.create_all()

        if reset:
            print("Reset flag detected: purging existing demonstration data...")
            # Delete in reverse foreign-key dependency order
            db.session.query(ClickEvent).delete()
            db.session.query(AdminLog).delete()
            db.session.execute(db.text("DELETE FROM link_tags"))
            db.session.query(Link).delete()
            db.session.query(Tag).delete()
            db.session.query(Campaign).delete()
            db.session.query(BlockedDomain).delete()
            db.session.query(User).delete()
            db.session.commit()
            print("Purge complete.")
        else:
            # Check if already seeded
            if User.query.filter_by(username='admin').first():
                print("Database already contains seed data.")
                print("Tip: Run 'python seed_data.py --reset' if you want to wipe and re-populate fresh demo data.")
                return

        print("Seeding Users...")
        # 1. Admin User
        admin_user = User(
            username='admin',
            email='admin@linkpulse.io',
            role='admin',
            is_active=True
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)

        # 2. Primary Demo User
        demo_user = User(
            username='alex_growth',
            email='demo@linkpulse.io',
            role='user',
            is_active=True
        )
        demo_user.set_password('demo123')
        db.session.add(demo_user)

        # 3. Secondary User
        sarah_user = User(
            username='sarah_m',
            email='sarah@growth.co',
            role='user',
            is_active=True
        )
        sarah_user.set_password('sarah123')
        db.session.add(sarah_user)

        db.session.commit()

        print("Seeding Blocked Domains & Audit Logs...")
        b1 = BlockedDomain(domain='phishing-paypal-security.com', reason='Credential harvesting phishing', created_by_user_id=admin_user.id)
        b2 = BlockedDomain(domain='free-crypto-giveaway-bot.xyz', reason='Cryptocurrency scam site', created_by_user_id=admin_user.id)
        b3 = BlockedDomain(domain='malware-download-cdn.top', reason='Malware distribution point', created_by_user_id=admin_user.id)
        db.session.add_all([b1, b2, b3])

        log1 = AdminLog(
            admin_user_id=admin_user.id,
            action='block_domain',
            target_type='domain',
            details='Blocked phishing-paypal-security.com following automated security report'
        )
        db.session.add(log1)
        db.session.commit()

        print("Seeding Campaigns & Tags for Demo User...")
        c1 = Campaign(user_id=demo_user.id, name='Q4 Global Product Launch', description='Marketing initiatives and product release pages for Q4.', color_code='#2563EB')
        c2 = Campaign(user_id=demo_user.id, name='Developer Outreach 2026', description='Technical guides, API documentation and GitHub promos.', color_code='#0EA5E9')
        c3 = Campaign(user_id=demo_user.id, name='Twitter Tech Blitz', description='Social media threads, memes, and viral posts.', color_code='#10B981')
        c4 = Campaign(user_id=demo_user.id, name='Weekly Newsletter', description='Curated reads and engineering articles.', color_code='#8B5CF6')
        db.session.add_all([c1, c2, c3, c4])

        t_github = Tag(user_id=demo_user.id, name='github', color_code='#2563EB')
        t_ai = Tag(user_id=demo_user.id, name='ai', color_code='#0EA5E9')
        t_docs = Tag(user_id=demo_user.id, name='docs', color_code='#10B981')
        t_social = Tag(user_id=demo_user.id, name='social', color_code='#F59E0B')
        t_analytics = Tag(user_id=demo_user.id, name='analytics', color_code='#8B5CF6')
        db.session.add_all([t_github, t_ai, t_docs, t_social, t_analytics])

        db.session.commit()

        print("Seeding Links...")
        now = get_utc_now()

        # Generate codes before link instantiation to avoid session autoflush conflicts
        codes = [generate_short_code() for _ in range(7)]

        with db.session.no_autoflush:
            # Link 1: Active popular link
            link1 = Link(
                user_id=demo_user.id,
                campaign_id=c2.id,
                short_code=codes[0],
                custom_alias='gh-trends',
                destination_url='https://github.com/trending',
                title='GitHub Trending Repositories',
                is_active=True,
                clicks_count=0,
                tags=[t_github, t_docs]
            )

            # Link 2: Tech News Link
            link2 = Link(
                user_id=demo_user.id,
                campaign_id=c4.id,
                short_code=codes[1],
                custom_alias='hackernews',
                destination_url='https://news.ycombinator.com',
                title='Hacker News Community Feed',
                is_active=True,
                clicks_count=0,
                tags=[t_ai]
            )

            # Link 3: Product Chart Demo
            link3 = Link(
                user_id=demo_user.id,
                campaign_id=c1.id,
                short_code=codes[2],
                custom_alias='chartjs-lib',
                destination_url='https://www.chartjs.org',
                title='Chart.js Data Visualization Library',
                is_active=True,
                clicks_count=0,
                tags=[t_analytics, t_docs]
            )

            # Link 4: Password Protected Link
            link4 = Link(
                user_id=demo_user.id,
                campaign_id=c1.id,
                short_code=codes[3],
                custom_alias='vip-access',
                destination_url='https://stripe.com/docs',
                title='VIP Merchant Documentation (Password Protected)',
                is_active=True,
                clicks_count=0,
                tags=[t_docs]
            )
            link4.set_password('partner2026')

            # Link 5: Limit Reached Link (Max clicks reached)
            link5 = Link(
                user_id=demo_user.id,
                campaign_id=c3.id,
                short_code=codes[4],
                custom_alias='early-beta',
                destination_url='https://openai.com/research',
                title='Early Beta Access Link (Cap: 25 clicks)',
                is_active=True,
                max_clicks=25,
                clicks_count=25,
                tags=[t_ai, t_social]
            )

            # Link 6: Expired Link
            link6 = Link(
                user_id=demo_user.id,
                campaign_id=c1.id,
                short_code=codes[5],
                custom_alias='summer-summit',
                destination_url='https://ted.com/talks',
                title='Summer Summit 2025 Event Replay (Expired)',
                is_active=True,
                expires_at=now - timedelta(days=15),
                clicks_count=18,
                tags=[t_social]
            )

            # Link 7: Temporarily Disabled Link
            link7 = Link(
                user_id=demo_user.id,
                campaign_id=c3.id,
                short_code=codes[6],
                custom_alias='promo-paused',
                destination_url='https://wikipedia.org/wiki/Web_analytics',
                title='Wiki Analytics Primer (Temporarily Paused)',
                is_active=False,
                clicks_count=12,
                tags=[t_analytics]
            )

            db.session.add_all([link1, link2, link3, link4, link5, link6, link7])

        db.session.commit()

        print("Generating Realistic Historical Click Analytics...")
        devices = ['desktop', 'desktop', 'desktop', 'mobile', 'mobile', 'tablet', 'bot']
        browsers = ['Chrome', 'Chrome', 'Chrome', 'Safari', 'Safari', 'Firefox', 'Edge']
        os_list = ['Windows', 'macOS', 'iOS', 'Android', 'Linux']
        referrers = [
            ('Direct', 'Direct'),
            ('https://twitter.com/dev_community/status/1234', 'twitter.com'),
            ('https://www.linkedin.com/feed/update/urn:li:activity:9876', 'linkedin.com'),
            ('https://github.com/topics/analytics', 'github.com'),
            ('https://news.ycombinator.com/item?id=4321', 'news.ycombinator.com'),
            ('https://www.google.com/search?q=best+url+shortener', 'google.com'),
        ]
        countries = [
            ('United States', 'San Francisco'),
            ('United States', 'New York'),
            ('India', 'Bengaluru'),
            ('United Kingdom', 'London'),
            ('Germany', 'Berlin'),
            ('Canada', 'Toronto'),
            ('Japan', 'Tokyo')
        ]

        active_demo_links = [link1, link2, link3, link4]
        click_events = []

        total_clicks_per_link = {
            link1.id: 0,
            link2.id: 0,
            link3.id: 0,
            link4.id: 0
        }

        for day_offset in range(14, -1, -1):
            date_base = now - timedelta(days=day_offset)
            clicks_today = random.randint(15, 35)
            for _ in range(clicks_today):
                target_link = random.choice(active_demo_links)
                click_time = date_base.replace(
                    hour=random.randint(8, 23),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                )

                dev = random.choice(devices)
                is_bot = (dev == 'bot')
                ref_url, ref_dom = random.choice(referrers)
                country, city = random.choice(countries)
                browser = random.choice(browsers)
                os_name = random.choice(os_list)
                ip = f"198.51.100.{random.randint(1, 250)}"
                v_hash = hashlib.sha256(f"{ip}:{browser}:{date_base.strftime('%Y-%m-%d')}".encode('utf-8')).hexdigest()[:32]

                event = ClickEvent(
                    link_id=target_link.id,
                    timestamp=click_time,
                    ip_address=ip,
                    country=country,
                    city=city,
                    referrer=ref_url,
                    referrer_domain=ref_dom,
                    user_agent=f"Mozilla/5.0 ({os_name}) AppleWebKit/537.36 ({browser})",
                    browser=browser,
                    os=os_name,
                    device_category=dev,
                    is_bot=is_bot,
                    visitor_hash=v_hash
                )
                click_events.append(event)
                total_clicks_per_link[target_link.id] += 1

        db.session.add_all(click_events)
        
        # Update link total counters
        for lid, count in total_clicks_per_link.items():
            db.session.query(Link).filter(Link.id == lid).update({Link.clicks_count: count})

        db.session.commit()
        print("Demo seed data successfully populated!")
        print("--------------------------------------------------")
        print("Admin Login: admin@linkpulse.io / admin123")
        print("Demo User Login: demo@linkpulse.io / demo123")
        print("--------------------------------------------------")

if __name__ == '__main__':
    reset_flag = '--reset' in sys.argv or '-r' in sys.argv
    seed_database(reset=reset_flag)
