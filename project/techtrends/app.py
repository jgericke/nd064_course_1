import sqlite3
import functools
import logging
from flask import (
    Flask,
    jsonify,
    json,
    render_template,
    request,
    url_for,
    redirect,
    flash,
    make_response,
)
from werkzeug.exceptions import abort


# Metrics wrapper for counting (read) connections to database
def metrics_collect(func):
    # Stores our global database read count
    metrics_collect.read_counter = 0
    # Wrap with functools to preserve function parameters
    @functools.wraps(func)
    def select_counter(*args, **kwargs):
        # Increment read count when a (decorated) function is called
        metrics_collect.read_counter += 1
        return func(*args, **kwargs)

    return select_counter


# Function to get a database connection.
# This function connects to database with the name `database.db`
def get_db_connection():
    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row
    return connection


# Function to get a post using its ID
def get_post(post_id):
    connection = get_db_connection()
    post = connection.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    connection.close()
    return post


# Define the Flask application
app = Flask(__name__)
app.config["SECRET_KEY"] = "your secret key"

# Define the main route of the web application
@app.route("/")
@metrics_collect
def index():
    connection = get_db_connection()
    posts = connection.execute("SELECT * FROM posts").fetchall()
    connection.close()
    return render_template("index.html", posts=posts)


# Define how each individual article is rendered
# If the post ID is not found a 404 page is shown
@app.route("/<int:post_id>")
@metrics_collect
def post(post_id):
    post = get_post(post_id)
    if post is None:
        app.logger.debug('Article id "{}" not found'.format(post_id))
        return render_template("404.html"), 404
    else:
        # Log article title
        app.logger.debug('Article "{}" retrieved!'.format(post["title"]))
        return render_template("post.html", post=post)


# Define the About Us page
@app.route("/about")
def about():
    app.logger.debug("About Us retrieved!")
    return render_template("about.html")


# Define the post creation functionality
@app.route("/create", methods=("GET", "POST"))
def create():
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]

        if not title:
            flash("Title is required!")
        else:
            connection = get_db_connection()
            connection.execute(
                "INSERT INTO posts (title, content) VALUES (?, ?)", (title, content)
            )
            connection.commit()
            connection.close()
            app.logger.debug('New article "{}" created!'.format(title))
            return redirect(url_for("index"))

    return render_template("create.html")


# Healthcheck endpoint
@app.route("/healthz", endpoint="healthcheck")
def healthcheck():
    healthcheck_resp = make_response(jsonify(result="OK - healthy"), 200)
    healthcheck_resp.mimetype = "application/json"
    return healthcheck_resp


# Metrics endpoint
@app.route("/metrics", endpoint="metrics")
@metrics_collect
def metrics():
    try:
        connection = get_db_connection()
        # Retrieve total posts for post_count
        post_count = connection.execute(
            "SELECT COUNT(id) FROM posts as posts_count"
        ).fetchone()[0]
    except Exception as e:
        app.logger.error(
            "Error occurred fetching total posts from database: {}".format(e)
        )
        raise

    # db_connection count is the total amount of connections to the database
    # counting read operations via metrics_collect.read_counter and write operations
    # via sqlite's builtin 'total_changes'
    # (https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.total_changes)
    db_connection_count = metrics_collect.read_counter + connection.total_changes
    metrics_resp = make_response(
        jsonify(db_connection_count=db_connection_count, post_count=post_count),
        200,
    )
    metrics_resp.mimetype = "application/json"

    return metrics_resp


# start the application on port 3111
if __name__ == "__main__":
    # Defines logging configuration
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s, %(message)s",
        datefmt="%d/%m/%Y, %H:%M:%S",
        handlers=[logging.StreamHandler()],
    )
    app.run(host="0.0.0.0", port="3111")
