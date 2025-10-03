from flask import render_template, redirect, flash, url_for
from app import app, db
from app.forms import LoginForm, RegistrationForm
from flask_login import current_user, login_user, logout_user, login_required
import sqlalchemy as sa
from app.models import User
from flask import request
from urllib.parse import urlsplit
from datetime import datetime, timezone

@app.route('/')
@app.route('/index')
@login_required
def index():
    user = {
        "username": "Reza"
    }
    posts = [
        {
            "author": {"username": "John"},
            "body": "Beautiful day in Portland!"
        },
        {
            "author": {"username": "Susan"},
            "body": "The Avengers movie was so cool!"
        }
    ]
    return render_template('index.html', title='Home Page', posts=posts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If the user is already logged in, don't show the login page again.
    # Send them to the home page instead.
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    # Build the WTForms form object (it will read data from request.form on POST).
    form = LoginForm()

    # True only on a POST with valid CSRF + all field validators passing.
    if form.validate_on_submit():
        # Fetch the user by username. We expect 0 or 1 row.
        # sa.select(User).where(...) builds the SQL; .scalar() returns the first column
        # of the first row (here the User entity) or None if no match.
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))

        # If no such user OR password doesn't match the stored hash → show an error.
        if user is None or not user.check_password(form.password.data):
            # Flash a one-time message stored in the session and shown on the next page.
            flash('Invalid username or password')
            # PRG pattern: redirect to the login page so a refresh doesn't resubmit the form.
            return redirect(url_for('login'))

        # Credentials are valid → log the user in.
        # `remember=` controls a long-lived session cookie if the user checked the box.
        login_user(user, remember=form.remember_me.data)

        # Get the "next" parameter from the query string (e.g. /login?next=/profile).
        # This parameter tells the app where the user wanted to go before being redirected to login.
        next_page = request.args.get('next')

        # If "next" is not provided OR it points to a full external URL (with a domain),
        # then redirect the user to the index page instead.
        # This prevents "open redirect" attacks, where a malicious site could trick users
        # into logging in and then redirect them outside your app.
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')

        # Finally, redirect the user to the safe destination.
        return redirect(next_page)

    # GET request (or failed POST): render the template with the form (and any flashed errors).
    return render_template('login.html',title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    posts = [
        {'author': user, 'body': 'Test post #1'},
        {'author': user, 'body': 'Test post #2'}
    ]
    return render_template('user.html', user=user, posts=posts)


# The @app.before_request decorator registers this function to run
# automatically before every request. It allows us to insert logic (like
# updating the user's last_seen timestamp) without repeating the same code
# in every route handler.
@app.before_request
# Update the user's "last_seen" timestamp to the current UTC time
# before handling each request (if the user is authenticated).
# Although the database column has a default value for when a new user is created,
# we use this to keep updating the field on each visit.
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        # No need to call db.session.add(current_user) because Flask-Login
        # already loads the user into the session.
        db.session.commit()