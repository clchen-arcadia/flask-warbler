import os

from dotenv import load_dotenv

from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import (
    CSRFProtectForm,
    UserAddForm,
    LoginForm,
    MessageForm,
    UserEditForm,
)
from models import db, connect_db, User, Message

# from urllib.parse import urlparse

load_dotenv()

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ['DATABASE_URL'].replace("postgres://", "postgresql://"))
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
toolbar = DebugToolbarExtension(app)

connect_db(app)


##############################################################################
# app.before_requests---these run before every request!

@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


@app.before_request
def add_csrf_to_g():
    """Add a csrf form to g"""

    g.csrf_form = CSRFProtectForm()


@app.before_request
def add_previous_url_to_g():
    """Add url of previous page before request to g."""

    g.previous_url = request.path
    g.test_url = request.url

##############################################################################
# app.after_requests---these run after every request!

# NOT INCLUDED: suboptimal for our use case!

# @app.after_request
# def add_history_to_session(resp):
#     """Add URL to history in the browser session"""

#     history = session.get('history', [])
#     history.append((
#         request.endpoint,
#         request.args,
#     ))


##############################################################################
# User signup/login/logout

def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Log out user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]
    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login and redirect to homepage on success."""

    form = LoginForm(username='username', password='password')

    if form.validate_on_submit():
        user = User.authenticate(
            form.username.data,
            form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.post('/logout')
def logout():
    """Handle logout of user and redirect to homepage."""

    form = g.csrf_form

    if form.validate_on_submit():
        do_logout()
        flash("Successful Logout")
        return redirect("/")

    else:
        flash("Unauthorized")
        return redirect("/")  # TODO: send them to 403 unauthorized


##############################################################################
# General user routes:

@app.get('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.get('/users/<int:user_id>')
def show_user(user_id):
    """Show user profile."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)

    return render_template('users/show.html', user=user)


@app.get('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)


@app.get('/users/<int:user_id>/likes')
def show_liked_messages(user_id):
    """Show list of messages this user has liked"""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/likes.html', user=user)


@app.get('/users/<int:user_id>/followers')
def show_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)


@app.post('/users/follow/<int:follow_id>')
def start_following(follow_id):
    """Add a follow for the currently-logged-in user.

    Redirect to following page for the current for the current user.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = g.csrf_form
    if form.validate_on_submit is False:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.post('/users/stop-following/<int:follow_id>')
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user.

    Redirect to following page for the current for the current user.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = g.csrf_form
    if form.validate_on_submit is False:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user."""

    if not g.user:
        flash("You must be logged in to edit profile!", "danger")
        return redirect("/")

    user = g.user

    form = UserEditForm(obj=user)

    if form.validate_on_submit():

        if User.authenticate(user.username, form.password.data) is False:
            flash("Incorrect password")
            return render_template("/users/edit.html", form=form)

        user.username = form.username.data
        user.email = form.email.data
        user.image_url = form.image_url.data
        user.header_image_url = form.header_image_url.data
        user.bio = form.bio.data

        db.session.commit()

        return redirect(f"/users/{user.id}")

    else:
        return render_template("/users/edit.html", form=form)


@app.post('/users/delete')
def delete_user():
    """Delete user.

    Redirect to signup page.
    """
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = g.csrf_form
    if form.validate_on_submit is False:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")


##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def add_message():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/create.html', form=form)


@app.get('/messages/<int:message_id>')
def show_message(message_id):
    """Show a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get_or_404(message_id)
    return render_template('messages/show.html', msg=msg)


@app.post('/messages/<int:message_id>/delete')
def delete_message(message_id):
    """Delete a message.

    Check that this message was written by the current user.
    Redirect to user page on success.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = g.csrf_form
    if form.validate_on_submit is False:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get_or_404(message_id)
    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


@app.post('/messages/<int:message_id>/like')
def like_message(message_id):
    """ Toggle liked message to database and fills icon to show liked status.
        Redirects to previous page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = g.csrf_form
    if form.validate_on_submit is False:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get_or_404(message_id)

    # g.user.toggle_liked(msg.id)

    # a higher level approach. SQLAlchemy power user:
    if msg in g.user.liked_messages:
        g.user.liked_messages.remove(msg)
    else:
        g.user.liked_messages.append(msg)
    db.session.commit()

    # DEPRECATED: this does not work across all browsers/privacy extensions!
    # url_parse = urlparse(request.referrer)
    # path = url_parse.path

    # should throw error if not in the form!
    go_back_to = request.form["from-url"]

    return redirect(go_back_to)


##############################################################################
# Homepage and error pages


@app.get('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    # Check is logged in
    if g.user:
        user = g.user

        # Generate a set containing ids of users whose posts we want to display
        # Includes current user id, and those they follow
        users_ids_list = [user.id for user in user.following]  # NOTE: name?
        users_ids_list.append(user.id)
        users_ids_set = set(users_ids_list)

        messages = (Message
                    .query
                    .filter(Message.user_id.in_(users_ids_set))
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())

        return render_template('home.html', messages=messages)

    else:
        return render_template('home-anon.html')


##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(response):
    """Add non-caching headers on every request."""

    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control
    response.cache_control.no_store = True
    return response
