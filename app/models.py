from datetime import datetime, timezone
from hashlib import md5
from typing import Optional

import sqlalchemy as sa
import sqlalchemy.orm as so
from flask_login import UserMixin
from sqlalchemy import PrimaryKeyConstraint
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login

# Association table for the "followers" relationship between users.
# This table implements a many-to-many relationship where:
# - one user can follow many other users
# - and one user can be followed by many users
# We use a plain Table (not a db.Model) because this table only stores
# the relationship itself and does not need its own model class.

followers = sa.Table(
    "followers",  # The actual name of the table in the database
    db.metadata,  # Registers this table in the application's metadata
    # (so that db.create_all() knows to create it)
    # The ID of the user who is following someone
    sa.Column(
        "follower_id",
        sa.Integer,
        sa.ForeignKey("user.id"),  # references user.id
        primary_key=True,
    ),  # part of the composite primary key
    # The ID of the user who is being followed
    sa.Column(
        "followed_id",
        sa.Integer,
        sa.ForeignKey("user.id"),  # also references user.id
        primary_key=True,
    ),  # part of the composite primary key
)

# Notes:
# - Both columns together form a composite primary key.
#   This means each (follower_id, followed_id) pair must be unique.
# - A user can follow multiple users, and be followed by multiple users.
# - You must define this table ABOVE the User model in models.py,
#   because the User model will reference it later.


class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    # so.WriteOnlyMapped, defines posts as a collection type with Post objects inside.
    posts: so.WriteOnlyMapped["Post"] = so.relationship(back_populates="author")

    # Relationship: list of users that this user is following
    following: so.WriteOnlyMapped["User"] = so.relationship(
        secondary=followers,
        # The association table that links users to each other (many-to-many)
        primaryjoin=(followers.c.follower_id == id),
        # How this user connects to the association table:
        # find all rows in 'followers' where follower_id == this user's id
        # → "which follow relationships start from me"
        secondaryjoin=(followers.c.followed_id == id),
        # How to connect from the association table to the target users:
        # match followers.followed_id with user.id of the other users
        # → "which users I'm following"
        back_populates="followers",
        # Links this relationship with the opposite side (followers),
        # so changes in one are automatically reflected in the other.
    )

    # Relationship: list of users that are following this user
    followers: so.WriteOnlyMapped["User"] = so.relationship(
        secondary=followers,
        # Same association table is used, but the join directions are reversed.
        primaryjoin=(followers.c.followed_id == id),
        # Now this user's id is matched with followed_id
        # → "find all rows where someone is following ME"
        secondaryjoin=(followers.c.follower_id == id),
        # Then match follower_id to get the user objects of those followers
        # → "which users are following me"
        back_populates="following",
        # Links back to the 'following' relationship for two-way sync.
    )

    def __repr__(self):
        return "<User {}>".format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode("utf-8")).hexdigest()
        return f"https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}"

    def follow(self, user):
        if not self.is_following(user):
            self.following.add(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.following.remove(user)

    def is_following(self, user):
        query = self.following.select().where(User.id == user.id)
        return db.ssesion.scalar(query) is not None

    def followers_count(self):
        query = sa.select(sa.func.count()).select_from(
            self.followers.select().subquery())
        return db.session.scalar(query)

    def following_count(self):
        query  = sa.select(sa.func.count()).select_from(
            self.following.select().subquery())
        return db.ssesion.scalar(query)

@login.user_loader
def load_user(id):
    # Flask-Login calls this function automatically
    # It receives the user ID stored in the session
    # We return the User object from the database that matches this ID
    return db.session.get(User, int(id))


class Post(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc)
    )
    # NOTE:
    # We use `lambda: datetime.now(timezone.utc)` instead of `datetime.now(timezone.utc)`.
    # - If we wrote `datetime.now(timezone.utc)`, it would be evaluated once at import time,
    #   and every new record would get the exact same fixed timestamp.
    # - By using a lambda (a callable), SQLAlchemy executes it each time a new record
    #   is created, so each record gets the *current* timestamp at insertion.
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id))

    author: so.Mapped[User] = so.relationship(back_populates="posts")

    def __repr__(self):
        return "<Post {}>".format(self.body)
