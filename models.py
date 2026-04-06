from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    avatar = db.Column(db.String(200), default='/static/default-avatar.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Друзья (многие ко многим)
    friends = db.relationship(
        'User', secondary='friends',
        primaryjoin=(id == db.Table('friends', db.Model.metadata,
                                    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                                    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'))
                                    ).c.user_id),
        secondaryjoin=(id == db.Table('friends', db.Model.metadata,
                                      db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                                      db.Column('friend_id', db.Integer, db.ForeignKey('user.id'))
                                      ).c.friend_id),
        lazy='dynamic'
    )