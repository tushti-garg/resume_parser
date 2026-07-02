from functools import wraps
from flask import session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db


def register_user(username, password):
    if not username or not password:
        return {"error": "Username and password required"}, 400
    if len(password) < 6:
        return {"error": "Password must be at least 6 characters"}, 400
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            return {"error": "Username already taken"}, 409
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
    return {"message": "Registered successfully"}, 201


def login_user(username, password):
    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
    if not user or not check_password_hash(user["password_hash"], password):
        return {"error": "Invalid username or password"}, 401
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return {"message": "Logged in", "username": user["username"]}, 200


def logout_user():
    session.clear()
    return {"message": "Logged out"}, 200


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return wrapper
