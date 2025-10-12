from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import logging
import os
from logging.handlers import SMTPHandler, RotatingFileHandler



app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)

# The 'login' value above is the function (or endpoint) name for the login view.
# In other words, the name you would use in a url_for() call to get the URL.
login.login_view = 'login'

#--- Sending Errors by Email ---
# This means that this code will only be activated when the application is running in production mode (not debug mode).
# Because in development mode you usually don't want to be emailed for every small error.
if not app.debug:
    # Checks if the email server information is defined in the config.
    # If not defined, it does nothing.
    if app.config['MAIL_SERVER']:
        # auth is a tuple of (username, password).
        auth = None
        if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
            auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        # 'secure' is for enabling TLS encryption in SMTP.
        # If secure = None → no TLS is used.
        # If secure = () → TLS is enabled with default settings (no extra options).
        # Usually used for secure email (e.g., Gmail).
        secure = None
        if app.config['MAIL_USE_TLS']:
            secure = ()
        mail_handler = SMTPHandler(
            mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
            fromaddr='no-reply@' + app.config['MAIL_SERVER'],
            toaddrs=app.config['ADMINS'],
            subject='Microblog Failure',
            credentials=auth,
            secure=secure
        )
        # Specifies that only logs with level ERROR or higher are sent to email.
        # INFO or DEBUG logs are not sent to email.
        mail_handler.setLevel(logging.ERROR)
        # Here SMTPHandler is added to Flask's default logging system (i.e. app.logger)
        # From now on, any error that occurs in the application → an ERROR log is created → this handler will catch it and email it
        app.logger.addHandler(mail_handler)

# --- Logging to a File ---
    if not os.path.exists('logs'):
        os.mkdir('logs')
    # Creates a RotatingFileHandler for logging to a file.
    # - 'logs/microblog.log' is the log file location.
    # - maxBytes=10240 → when the log file reaches ~10KB, it will rotate (create a new file)
    # - backupCount=10 → keeps up to 10 old log files (e.g., microblog.log.1, microblog.log.2, ...)
    file_handler = RotatingFileHandler('logs/microblog.log', maxBytes=10240, backupCount=10)

    # Sets the format of each log entry.
    # Example output:
    # 2025-10-12 10:30:45,123 INFO: Microblog startup
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))

    # Sets the log level for the file handler.
    # Only logs with level INFO or higher will be saved to the file.
    # In case you are not familiar with the logging categories, they are DEBUG, INFO, WARNING, ERROR and CRITICAL in increasing order of severity.
    file_handler.setLevel(logging.INFO)

    # Adds this file handler to Flask's default logger (app.logger).
    # From now on, logs will be written both to the console (by default) and to the log file.
    app.logger.addHandler(file_handler)

    # Sets the overall logging level of the application to INFO.
    # This means DEBUG messages will be ignored, but INFO and above will be logged.
    app.logger.setLevel(logging.INFO)

    # Writes an INFO log indicating that the application has started.
    # This will appear in the log file as the first entry.
    # It's mostly to know when and how many times the program was started.
    app.logger.info('Microblog startup')

from app import routes, models, errors
