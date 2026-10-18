from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models.tag import link_tags

class Link(db.Model):
    __tablename__ = 'links'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id', ondelete='SET NULL'), nullable=True, index=True)
    
    short_code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    custom_alias = db.Column(db.String(64), unique=True, nullable=True, index=True)
    destination_url = db.Column(db.Text, nullable=False)
    title = db.Column(db.String(255), nullable=True)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True, index=True)
    max_clicks = db.Column(db.Integer, nullable=True)
    clicks_count = db.Column(db.Integer, default=0, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tags = db.relationship('Tag', secondary=link_tags, backref=db.backref('links', lazy='dynamic'), lazy='subquery')
    click_events = db.relationship('ClickEvent', backref='link', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password: str):
        if password and password.strip():
            self.password_hash = generate_password_hash(password.strip())
        else:
            self.password_hash = None

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return True
        if not password:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_password_protected(self) -> bool:
        return bool(self.password_hash)

    @property
    def is_expired(self) -> bool:
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False

    @property
    def is_limit_reached(self) -> bool:
        if self.max_clicks is not None and self.max_clicks > 0:
            return self.clicks_count >= self.max_clicks
        return False

    @property
    def status(self) -> str:
        if not self.is_active:
            return 'disabled'
        if self.is_expired:
            return 'expired'
        if self.is_limit_reached:
            return 'limit_reached'
        return 'active'

    @property
    def effective_code(self) -> str:
        return self.custom_alias if self.custom_alias else self.short_code

    def to_dict(self, base_url=""):
        code = self.effective_code
        short_url = f"{base_url}/r/{code}" if base_url else f"/r/{code}"
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'campaign_id': self.campaign_id,
            'campaign_name': self.campaign.name if self.campaign else None,
            'short_code': self.short_code,
            'custom_alias': self.custom_alias,
            'effective_code': code,
            'short_url': short_url,
            'destination_url': self.destination_url,
            'title': self.title or self.destination_url,
            'is_active': self.is_active,
            'status': self.status,
            'is_password_protected': self.is_password_protected,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'max_clicks': self.max_clicks,
            'clicks_count': self.clicks_count,
            'tags': [t.to_dict() for t in self.tags],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Link {self.effective_code} -> {self.destination_url[:30]}>'
