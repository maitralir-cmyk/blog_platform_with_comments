# InkSpace – Blog Platform with Comments

A beginner-friendly full-stack blogging application built with **HTML, CSS, JavaScript, Python Flask, and SQLite**.

## Features
- Register and log in with password hashing
- Create, read, update, and delete your own blog posts
- Add comments and delete your own comments
- User dashboard
- SQLite database with users, posts, and comments tables
- JSON REST API for listing posts and viewing a post with comments
- Responsive layout for desktop and mobile

## Requirements
- Python 3.9 or newer
- pip

## Run on Windows
1. Extract the ZIP file.
2. Open the extracted `blog_platform_with_comments` folder in VS Code.
3. Open Terminal in VS Code.
4. (Recommended) Create a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
6. Start the application:
   ```bash
   python app.py
   ```
7. Open **http://127.0.0.1:5000** in your browser.
8. Register an account and start publishing posts.

The `blog.db` database is created automatically the first time the application starts.

## REST API
- `GET /api/posts` – return all posts as JSON
- `GET /api/posts/<post_id>` – return one post and its comments as JSON

Example: visit `http://127.0.0.1:5000/api/posts` after starting the app.

## Project structure
```text
blog_platform_with_comments/
│ app.py
│ requirements.txt
│ README.md
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── register.html
│   ├── login.html
│   ├── dashboard.html
│   ├── post_form.html
│   ├── post.html
│   └── error.html
└── static/
    ├── css/style.css
    └── js/main.js
```

## Important before deployment
This is a learning/demo project. Before public deployment:
- Set a long, random `SECRET_KEY` using an environment variable.
- Turn off Flask debug mode (`debug=False`).
- Add CSRF protection, rate limiting, secure cookie settings, and production hosting.
- Use HTTPS and back up the database.
- The app currently uses SQLite, which is suitable for a small demo; consider PostgreSQL for a larger public service.

## Database design
- `users`: account details and hashed passwords
- `posts`: blog title, content, author, timestamps
- `comments`: comment content, post, author, timestamp

Deleting a user or post cascades to their related records.
