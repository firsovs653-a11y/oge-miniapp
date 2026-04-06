from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# Таблица для связи друзей (многие ко многим)
friends = db.Table('friends',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

# Таблица для заявок в друзья
class FriendRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    from_user = db.relationship('User', foreign_keys=[from_user_id], backref='sent_requests')
    to_user = db.relationship('User', foreign_keys=[to_user_id], backref='received_requests')

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    avatar = db.Column(db.String(200), default='/static/default-avatar.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Друзья
    friends = db.relationship(
        'User',
        secondary=friends,
        primaryjoin=(id == friends.c.user_id),
        secondaryjoin=(id == friends.c.friend_id),
        lazy='dynamic'
    )
