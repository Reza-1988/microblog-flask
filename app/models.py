from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from app import db
from flask_login import UserMixin
from app import login
from hashlib import md5

class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    about_me:so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    last_seen:so.Mapped[Optional[datetime]] = so.mapped_column(
        default=lambda:datetime.now(timezone.utc))

    # so.WriteOnlyMapped, defines posts as a collection type with Post objects inside.
    posts: so.WriteOnlyMapped['Post'] = so.relationship(back_populates='author')



    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f"https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}"


@ login.user_loader
def load_user(id):
    # Flask-Login calls this function automatically
    # It receives the user ID stored in the session
    # We return the User object from the database that matches this ID
    return db.session.get(User, int(id))


class Post(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda:datetime.now(timezone.utc)
    )
    # NOTE:
    # We use `lambda: datetime.now(timezone.utc)` instead of `datetime.now(timezone.utc)`.
    # - If we wrote `datetime.now(timezone.utc)`, it would be evaluated once at import time,
    #   and every new record would get the exact same fixed timestamp.
    # - By using a lambda (a callable), SQLAlchemy executes it each time a new record
    #   is created, so each record gets the *current* timestamp at insertion.
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id))

    author: so.Mapped[User] = so.relationship(back_populates='posts')

    def __repr__(self):
        return '<Post {}>'.format(self.body)
