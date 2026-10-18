from datetime import datetime
from app.extensions import db

class ClickEvent(db.Model):
    __tablename__ = 'click_events'

    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(db.Integer, db.ForeignKey('links.id', ondelete='CASCADE'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    ip_address = db.Column(db.String(45), nullable=True)
    country = db.Column(db.String(64), default='Unknown', nullable=False)
    city = db.Column(db.String(64), default='Unknown', nullable=False)
    
    referrer = db.Column(db.String(512), default='Direct', nullable=False)
    referrer_domain = db.Column(db.String(128), default='Direct', nullable=False)
    
    user_agent = db.Column(db.Text, nullable=True)
    browser = db.Column(db.String(64), default='Unknown', nullable=False)
    os = db.Column(db.String(64), default='Unknown', nullable=False)
    device_category = db.Column(db.String(32), default='desktop', nullable=False) # desktop, mobile, tablet, bot
    
    is_bot = db.Column(db.Boolean, default=False, nullable=False, index=True)
    visitor_hash = db.Column(db.String(64), nullable=True, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'link_id': self.link_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'country': self.country,
            'city': self.city,
            'referrer': self.referrer,
            'referrer_domain': self.referrer_domain,
            'browser': self.browser,
            'os': self.os,
            'device_category': self.device_category,
            'is_bot': self.is_bot
        }

    def __repr__(self):
        return f'<ClickEvent Link:{self.link_id} at {self.timestamp} from {self.browser}/{self.os}>'
