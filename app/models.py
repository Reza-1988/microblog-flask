from datetime import datetime, timezone
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from app import db


class User(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))

    posts: so.WriteOnlyMapped['Post'] = so.relationship(back_populates='author')
    # so.WriteOnlyMapped, defines posts as a collection type with Post objects inside.

    def __repr__(self):
        return '<User {}>'.format(self.username)

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