from datetime import datetime
from app.extensions import db

class BlockedDomain(db.Model):
    __tablename__ = 'blocked_domains'

    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(255), unique=True, nullable=False, index=True)
    reason = db.Column(db.String(255), default='Suspicious or malicious domain', nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    creator = db.relationship('User', foreign_keys=[created_by_user_id])

    def to_dict(self):
        return {
            'id': self.id,
            'domain': self.domain,
            'reason': self.reason,
            'is_active': self.is_active,
            'created_by': self.creator.username if self.creator else 'System',
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<BlockedDomain {self.domain}>'
