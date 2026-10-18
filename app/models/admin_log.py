from datetime import datetime
from app.extensions import db

class AdminLog(db.Model):
    __tablename__ = 'admin_logs'

    id = db.Column(db.Integer, primary_key=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(64), nullable=False) # e.g., 'disable_link', 'block_domain', 'change_role'
    target_type = db.Column(db.String(64), nullable=False) # e.g., 'link', 'domain', 'user'
    target_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    admin = db.relationship('User', foreign_keys=[admin_user_id])

    def to_dict(self):
        return {
            'id': self.id,
            'admin_username': self.admin.username if self.admin else 'System',
            'action': self.action,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<AdminLog {self.action} on {self.target_type}:{self.target_id}>'
