from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
import sqlalchemy as sa
from app import db
from app.models import User


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Real Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    # When you add any methods that match the pattern validate_<field_name>,
    # WTForms takes those as custom validators and invokes them in addition to the stock validators.
    # I have added two of those methods to this class for the username and email fields.
    # In this case I want to make sure that the username and email address entered by the user are not already in the database,
    # so these two methods issue database queries expecting there will be no results.

    def validate_username(self, username):
        user = db.session.scalar(sa.select(User).where(
            User.username == username.data
        ))
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = db.session.scalar(sa.select(User).where(
                User.email == email.data
        ))
        if user is not None:
            raise ValidationError('Please use a different email address.')