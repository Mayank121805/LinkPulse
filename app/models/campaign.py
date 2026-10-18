from datetime import datetime
from app.extensions import db

class Campaign(db.Model):
    __tablename__ = 'campaigns'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    color_code = db.Column(db.String(20), default='#2563EB', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    links = db.relationship('Link', backref='campaign', lazy='dynamic')

    def to_dict(self, include_stats=False):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'color_code': self.color_code,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_stats:
            links_list = self.links.all()
            data['links_count'] = len(links_list)
            data['total_clicks'] = sum(link.clicks_count for link in links_list)
        return data

    def __repr__(self):
        return f'<Campaign {self.name}>'
