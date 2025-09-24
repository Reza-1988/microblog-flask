from flask import render_template, redirect, flash, url_for
from app import app, db
from app.forms import LoginForm
from flask_login import current_user, login_user
import sqlalchemy as sa
from app.models import User

@app.route('/')
@app.route('/index')
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
    return render_template('index.html', user=user, posts=posts)

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

    # GET request (or failed POST): render the template with the form (and any flashed errors).
    return render_template('login.html',title='Sign In', form=form)