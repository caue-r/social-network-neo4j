"""Simple Flask interface for the Neo4j social network demo."""
from __future__ import annotations

import os
from contextlib import contextmanager
from functools import wraps
from typing import Iterator, List, Optional

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from social_network import service
from social_network.neo4j_client import Neo4jClient

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")


@contextmanager
def get_client() -> Iterator[Neo4jClient]:
    client = Neo4jClient()
    try:
        yield client
    finally:
        client.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("auth_user"):
            flash("Faça login para acessar esta área.", "error")
            return redirect(url_for("index"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Área restrita ao administrador.", "error")
            return redirect(url_for("admin_dashboard"))
        return view(*args, **kwargs)

    return wrapped


def render_dashboard(**context):
    """Render the authenticated dashboard with defaults."""
    auth_user = session.get("auth_user")
    default_context = {
        "feed": None,
        "feed_username": auth_user["username"] if auth_user else None,
        "feed_limit": 25,
        "auth_user": auth_user,
    }
    default_context.update(context)
    return render_template("dashboard.html", **default_context)


def render_admin_dashboard(**context):
    """Render the admin dashboard with base context."""
    default_context = {
        "is_admin": bool(session.get("is_admin")),
        "search_results": [],
        "search_query": "",
    }
    default_context.update(context)
    return render_template("admin.html", **default_context)


@app.route("/", methods=["GET"])
def index():
    if session.get("auth_user"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login_page"))


@app.get("/login")
def login_page():
    if session.get("auth_user"):
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.get("/register")
def register_page():
    if session.get("auth_user"):
        return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.get("/dashboard")
@login_required
def dashboard():
    return render_dashboard()

@app.get("/admin")
def admin_dashboard():
    search_query = request.args.get("q", "").strip()
    search_results = []
    if session.get("is_admin"):
        try:
            with get_client() as client:
                search_results = service.admin_search_users(client, search_query)
        except Exception as exc:  # pragma: no cover - feedback ao usuário
            flash(f"Erro ao buscar usuários: {exc}", "error")
    return render_admin_dashboard(search_results=search_results, search_query=search_query)


@app.post("/create-user")
@login_required
def create_user():
    username = request.form.get("username", "").strip()
    name = request.form.get("name", "").strip()
    bio = request.form.get("bio", "").strip()

    if not username or not name:
        flash("Username e nome são obrigatórios.", "error")
        return redirect(url_for("dashboard"))

    try:
        with get_client() as client:
            service.create_user(client, username, name, bio)
    except Exception as exc:  # pragma: no cover - feedback ao usuário
        flash(f"Erro ao criar usuário: {exc}", "error")
    else:
        flash(f"Usuário @{username} criado/atualizado com sucesso.", "success")
    return redirect(url_for("dashboard"))


@app.post("/follow")
@login_required
def follow():
    follows = request.form.get("follows", "").strip()
    auth_user = session["auth_user"]

    if not follows:
        flash("Informe quem será seguido.", "error")
        return redirect(url_for("dashboard"))

    try:
        with get_client() as client:
            service.add_follow(client, auth_user["username"], follows)
    except Exception as exc:  # pragma: no cover - feedback ao usuário
        flash(f"Erro ao seguir usuário: {exc}", "error")
    else:
        flash(f"@{auth_user['username']} agora segue @{follows}.", "success")
    return redirect(url_for("dashboard"))


@app.post("/create-post")
@login_required
def create_post():
    content = request.form.get("content", "").strip()
    auth_user = session["auth_user"]

    if not content:
        flash("Conteúdo do post é obrigatório.", "error")
        return redirect(url_for("dashboard"))

    try:
        with get_client() as client:
            service.create_post(client, auth_user["username"], content)
    except Exception as exc:  # pragma: no cover - feedback ao usuário
        flash(f"Erro ao criar post: {exc}", "error")
    else:
        flash("Post publicado com sucesso.", "success")
    return redirect(url_for("dashboard"))


@app.post("/feed")
@login_required
def fetch_feed():
    limit_raw = request.form.get("limit", "25").strip()
    auth_user = session["auth_user"]

    try:
        limit = int(limit_raw)
    except ValueError:
        limit = 25

    feed: Optional[List[dict]] = None
    try:
        with get_client() as client:
            feed = service.fetch_feed(client, auth_user["username"], limit=limit)
    except Exception as exc:  # pragma: no cover - feedback ao usuário
        flash(f"Erro ao buscar feed: {exc}", "error")
        return redirect(url_for("dashboard"))

    return render_dashboard(feed=feed, feed_username=auth_user["username"], feed_limit=limit)


@app.post("/register")
def register():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "").strip()

    if not all([name, email, username, password]):
        flash("Nome, email, usuário e senha são obrigatórios.", "error")
        return redirect(url_for("register_page"))

    try:
        password_hash = generate_password_hash(password)
        with get_client() as client:
            service.register_account(
                client,
                name=name,
                email=email,
                username=username,
                password_hash=password_hash,
            )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("register_page"))
    except Exception as exc:  # pragma: no cover - feedback ao usuário
        flash(f"Erro ao cadastrar usuário: {exc}", "error")
        return redirect(url_for("register_page"))
    else:
        flash("Cadastro realizado com sucesso. Você já pode fazer login.", "success")
        return redirect(url_for("login_page"))


@app.post("/login")
def login():
    identifier = request.form.get("identifier", "").strip().lower()
    password = request.form.get("password", "")

    if not identifier or not password:
        flash("Informe usuário ou email e a senha.", "error")
        return redirect(url_for("login_page"))

    try:
        with get_client() as client:
            user = service.find_user_for_login(client, identifier)
    except Exception as exc:  # pragma: no cover - feedback ao usuário
        flash(f"Erro ao consultar usuário: {exc}", "error")
        return redirect(url_for("login_page"))

    if not user or not user.get("password_hash") or not check_password_hash(
        user["password_hash"], password
    ):
        flash("Credenciais inválidas.", "error")
        return redirect(url_for("login_page"))

    session["auth_user"] = {
        "username": user.get("username"),
        "name": user.get("name"),
        "email": user.get("email"),
    }
    flash(f"Bem-vindo, {user.get('name') or user.get('username')}!", "success")
    return redirect(url_for("dashboard"))


@app.post("/logout")
def logout():
    session.pop("auth_user", None)
    session.pop("is_admin", None)
    flash("Sessão encerrada.", "success")
    return redirect(url_for("index"))


@app.post("/admin/login")
def admin_login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session["is_admin"] = True
        flash("Login de administrador realizado com sucesso.", "success")
    else:
        flash("Credenciais de administrador inválidas.", "error")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/logout")
@admin_required
def admin_logout():
    session.pop("is_admin", None)
    flash("Sessão de administrador encerrada.", "success")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/users/create")
@admin_required
def admin_create_user_action():
    username = request.form.get("username", "").strip()
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    bio = request.form.get("bio", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        flash("Username e senha são obrigatórios para criar usuários.", "error")
        return redirect(url_for("admin_dashboard"))

    try:
        password_hash = generate_password_hash(password)
        with get_client() as client:
            service.admin_create_user(
                client,
                username=username,
                password_hash=password_hash,
                name=name,
                email=email or None,
                bio=bio,
            )
    except Exception as exc:  # pragma: no cover - feedback ao usuário
        flash(f"Erro ao criar usuário: {exc}", "error")
    else:
        flash(f"Usuário @{username} criado com sucesso.", "success")
    return redirect(url_for("admin_dashboard", q=username))


@app.post("/admin/users/update")
@admin_required
def admin_update_user_action():
    original_username = request.form.get("original_username", "").strip()
    if not original_username:
        flash("Usuário original é obrigatório.", "error")
        return redirect(url_for("admin_dashboard"))

    new_username = request.form.get("username", "").strip()
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    bio = request.form.get("bio", "").strip()
    password = request.form.get("password", "").strip()

    password_hash = generate_password_hash(password) if password else None

    try:
        with get_client() as client:
            updated_user = service.admin_update_user(
                client,
                username=original_username,
                new_username=new_username if new_username and new_username != original_username else None,
                name=name,
                email=email,
                bio=bio,
                password_hash=password_hash,
            )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin_dashboard", q=original_username))
    except Exception as exc:  # pragma: no cover - feedback ao usuário
        flash(f"Erro ao atualizar usuário: {exc}", "error")
        return redirect(url_for("admin_dashboard", q=original_username))

    flash(f"Usuário @{updated_user['username']} atualizado com sucesso.", "success")
    return redirect(url_for("admin_dashboard", q=updated_user["username"]))


@app.post("/admin/users/delete")
@admin_required
def admin_delete_user_action():
    username = request.form.get("username", "").strip()
    if not username:
        flash("Informe o usuário que será removido.", "error")
        return redirect(url_for("admin_dashboard"))

    try:
        with get_client() as client:
            service.admin_delete_user(client, username)
    except ValueError as exc:
        flash(str(exc), "error")
    except Exception as exc:  # pragma: no cover - feedback ao usuário
        flash(f"Erro ao remover usuário: {exc}", "error")
    else:
        flash(f"Usuário @{username} removido com sucesso.", "success")
    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
