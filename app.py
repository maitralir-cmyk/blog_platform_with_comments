from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
from pathlib import Path

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key-before-deployment"
DB_PATH = Path(__file__).with_name("blog.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

@app.context_processor
def inject_user():
    return {"current_user": session.get("username"), "current_user_id": session.get("user_id")}

@app.route("/")
def index():
    with get_db() as db:
        posts = db.execute("""
            SELECT posts.*, users.username,
                   (SELECT COUNT(*) FROM comments WHERE comments.post_id = posts.id) AS comment_count
            FROM posts JOIN users ON users.id = posts.user_id
            ORDER BY posts.created_at DESC
        """).fetchall()
    return render_template("index.html", posts=posts)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if len(username) < 3 or len(password) < 8 or "@" not in email:
            flash("Use a username of at least 3 characters, a valid email, and a password of at least 8 characters.", "error")
            return render_template("register.html")
        try:
            with get_db() as db:
                db.execute("INSERT INTO users(username,email,password_hash) VALUES(?,?,?)",
                           (username, email, generate_password_hash(password)))
            flash("Account created. You can now log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("That username or email is already registered.", "error")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        password = request.form.get("password", "")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE username=? OR email=?", (identity, identity.lower())).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))
        flash("Incorrect username/email or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    with get_db() as db:
        posts = db.execute("""
            SELECT posts.*, (SELECT COUNT(*) FROM comments WHERE comments.post_id=posts.id) AS comment_count
            FROM posts WHERE user_id=? ORDER BY created_at DESC
        """, (session["user_id"],)).fetchall()
    return render_template("dashboard.html", posts=posts)

@app.route("/post/new", methods=["GET", "POST"])
@login_required
def new_post():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if not title or not content:
            flash("Title and content are required.", "error")
        else:
            with get_db() as db:
                db.execute("INSERT INTO posts(user_id,title,content) VALUES(?,?,?)",
                           (session["user_id"], title, content))
            flash("Your post has been published.", "success")
            return redirect(url_for("dashboard"))
    return render_template("post_form.html", post=None)

@app.route("/post/<int:post_id>")
def view_post(post_id):
    with get_db() as db:
        post = db.execute("""
            SELECT posts.*, users.username FROM posts JOIN users ON users.id=posts.user_id
            WHERE posts.id=?
        """, (post_id,)).fetchone()
        if not post:
            abort(404)
        comments = db.execute("""
            SELECT comments.*, users.username FROM comments
            JOIN users ON users.id=comments.user_id
            WHERE post_id=? ORDER BY comments.created_at ASC
        """, (post_id,)).fetchall()
    return render_template("post.html", post=post, comments=comments)

@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    with get_db() as db:
        post = db.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
        if not post:
            abort(404)
        if post["user_id"] != session["user_id"]:
            abort(403)
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            if title and content:
                db.execute("UPDATE posts SET title=?, content=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                           (title, content, post_id))
                flash("Post updated.", "success")
                return redirect(url_for("dashboard"))
            flash("Title and content are required.", "error")
    return render_template("post_form.html", post=post)

@app.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    with get_db() as db:
        post = db.execute("SELECT user_id FROM posts WHERE id=?", (post_id,)).fetchone()
        if not post:
            abort(404)
        if post["user_id"] != session["user_id"]:
            abort(403)
        db.execute("DELETE FROM posts WHERE id=?", (post_id,))
    flash("Post deleted.", "success")
    return redirect(url_for("dashboard"))

@app.route("/post/<int:post_id>/comment", methods=["POST"])
@login_required
def add_comment(post_id):
    content = request.form.get("content", "").strip()
    if not content:
        flash("Please write a comment first.", "error")
    else:
        with get_db() as db:
            exists = db.execute("SELECT id FROM posts WHERE id=?", (post_id,)).fetchone()
            if not exists:
                abort(404)
            db.execute("INSERT INTO comments(post_id,user_id,content) VALUES(?,?,?)",
                       (post_id, session["user_id"], content))
        flash("Comment added.", "success")
    return redirect(url_for("view_post", post_id=post_id) + "#comments")

@app.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    with get_db() as db:
        comment = db.execute("SELECT * FROM comments WHERE id=?", (comment_id,)).fetchone()
        if not comment:
            abort(404)
        post_id = comment["post_id"]
        if comment["user_id"] != session["user_id"]:
            abort(403)
        db.execute("DELETE FROM comments WHERE id=?", (comment_id,))
    flash("Comment deleted.", "success")
    return redirect(url_for("view_post", post_id=post_id) + "#comments")

# REST API: JSON endpoints for posts and comments
@app.route("/api/posts", methods=["GET"])
def api_posts():
    with get_db() as db:
        rows = db.execute("""
            SELECT posts.id, posts.title, posts.content, posts.created_at, users.username
            FROM posts JOIN users ON users.id=posts.user_id ORDER BY posts.created_at DESC
        """).fetchall()
    return jsonify([dict(row) for row in rows])

@app.route("/api/posts/<int:post_id>", methods=["GET"])
def api_post_detail(post_id):
    with get_db() as db:
        post = db.execute("SELECT id,title,content,created_at FROM posts WHERE id=?", (post_id,)).fetchone()
        if not post:
            return jsonify({"error": "Post not found"}), 404
        comments = db.execute("""
            SELECT comments.id, comments.content, comments.created_at, users.username
            FROM comments JOIN users ON users.id=comments.user_id
            WHERE post_id=? ORDER BY comments.created_at
        """, (post_id,)).fetchall()
    return jsonify({"post": dict(post), "comments": [dict(row) for row in comments]})

@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, message="You don't have permission to do that."), 403

@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, message="The page or post could not be found."), 404

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
