import sqlalchemy as sa
import sqlalchemy.orm as so
from app import app, db
from app.models import User, Post

@app.shell_context_processor
def make_shell_context():
    return dict(app=app, db=db, User=User, Post=Post)
# The @app.shell_context_processor decorator tells Flask that this function
# should be used to define the "shell context".
# Whenever you run `flask shell`, Flask will call this function and automatically
# import the returned objects into the shell session.
# We return a dictionary (not a list) because each object must be given a name
# (the dict key) so it can be referenced directly in the shell, e.g. `db`, `User`, `Post`.
