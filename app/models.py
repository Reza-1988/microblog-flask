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

    # Follow another user (create the relationship in the association table)
    def follow(self, user):
        # Only add if the relationship doesn't already exist
        if not self.is_following(user):
            # self.following is a relationship (many-to-many)
            # .add() works if the relationship is a set; use .append() if it's a list
            self.following.add(user)

    # Unfollow a user (remove the relationship from the association table)
    def unfollow(self, user):
        # Only remove if the relationship currently exists
        if self.is_following(user):
            self.following.remove(user)

    # Check if the current user is following another user
    def is_following(self, user):
        # self.following.select() builds a SELECT query based on the "following" relationship
        # It joins the association table + users table behind the scenes,
        # and filters all rows where follower_id = self.id.
        query = self.following.select().where(User.id == user.id)
        # The WHERE condition limits results to a single user (the one passed as argument)
        # e.g. ... WHERE followers.follower_id = self.id AND users.id = user.id

        # scalar(query) executes the query and returns the first value of the first row,
        # or None if there is no match.
        return db.session.scalar(query) is not None

    # Count how many users follow this user
    def followers_count(self):
        # Build a subquery from the "followers" relationship (users following self)
        # This generates something like:
        #   SELECT users.* FROM followers
        #   JOIN users ON followers.follower_id = users.id
        #   WHERE followers.followed_id = self.id
        inner_query = self.followers.select().subquery()

        # Wrap that subquery in a COUNT(*) query:
        #   SELECT COUNT(*) FROM (inner_query) AS anon
        count_query = sa.select(sa.func.count()).select_from(inner_query)

        # Execute and return the scalar count result
        return db.session.scalar(count_query)

    # Count how many users this user is following
    def following_count(self):
        # Similar logic, but using the "following" relationship
        # → users that self is following
        inner_query = self.following.select().subquery()
        count_query = sa.select(sa.func.count()).select_from(inner_query)
        return db.session.scalar(count_query)

    def following_posts(self):
        # 1. Create aliases for the User table so we can use it twice in the same query:
        # - Author: represents the users who WROTE the posts
        # - Follower: represents the users who FOLLOW those authors
        # (Using aliases prevents confusion when joining the same table twice)
        Author = so.aliased(User)
        Follower = so.aliased(User)

        return (
            sa.select(Post)
            # 2. Start building the query by selecting posts as the main result.

            # 3. Join the Post table to the User table (as Author) through the 'author' relationship.
            # SQLAlchemy automatically knows that this means:
            #   post.user_id = author.id
            # So now, each Post row is connected to the User (Author) who wrote it.
            .join(Post.author.of_type(Author))

            # 4. Join again — this time from the Author to their followers.
            # 'Author.followers' uses the many-to-many association table "followers"
            # that connects authors to the users who follow them.
            # Setting `isouter=True` means we use a LEFT OUTER JOIN,
            # so that even if an author has NO followers, their posts still appear.
            .join(Author.followers.of_type(Follower), isouter=True)

            # 5. Add a WHERE condition to limit which posts we see.
            # The condition uses OR to include two cases:
            #   a) Follower.id == self.id  → posts from authors that the current user follows
            #   b) Author.id == self.id    → posts written by the current user themselves
            # This ensures the feed shows both the user's own posts and their followings’ posts.
            .where(sa.or_(
                Follower.id == self.id,
                Author.id == self.id,
            ))

            # 6. Group by Post to remove duplicate rows.
            # Why? Because one author can have multiple followers, which would create
            # multiple identical rows for the same post after the join.
            # GROUP BY Post collapses those duplicates into a single row per post.
            .group_by(Post)

            # 7. Finally, order the posts from newest to oldest.
            .order_by(Post.timestamp.desc())
        )


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
