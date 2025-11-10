"""Simple Flask interface for the Neo4j social network demo."""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, List, Optional

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for

from social_network import service
from social_network.neo4j_client import Neo4jClient

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")


@contextmanager
def get_client() -> Iterator[Neo4jClient]:
    client = Neo4jClient()
    try:
        yield client
    finally:
        client.close()


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", feed=None, feed_username=None, feed_limit=25)


@app.post("/create-user")
def create_user():
    username = request.form.get("username", "").strip()
    name = request.form.get("name", "").strip()
    bio = request.form.get("bio", "").strip()

    if not username or not name:
        flash("Username e nome são obrigatórios.", "error")
        return redirect(url_for("index"))

    try:
        with get_client() as client:
            service.create_user(client, username, name, bio)
    except Exception as exc:  # pragma: no cover - feedback ao usuário
        flash(f"Erro ao criar usuário: {exc}", "error")
    else:
        flash(f"Usuário @{username} criado/atualizado com sucesso.", "success")
    return redirect(url_for("index"))


@app.post("/follow")
def follow():
    username = request.form.get("username", "").strip()
    follows = request.form.get("follows", "").strip()

    if not username or not follows:
        flash("Informe quem segue e quem será seguido.", "error")
        return redirect(url_for("index"))

    try:
        with get_client() as client:
            service.add_follow(client, username, follows)
    except Exception as exc:  # pragma: no cover - feedback ao usuário
        flash(f"Erro ao seguir usuário: {exc}", "error")
    else:
        flash(f"@{username} agora segue @{follows}.", "success")
    return redirect(url_for("index"))


@app.post("/create-post")
def create_post():
    username = request.form.get("username", "").strip()
    content = request.form.get("content", "").strip()

    if not username or not content:
        flash("Usuário e conteúdo do post são obrigatórios.", "error")
        return redirect(url_for("index"))

    try:
        with get_client() as client:
            service.create_post(client, username, content)
    except Exception as exc:  # pragma: no cover - feedback ao usuário
        flash(f"Erro ao criar post: {exc}", "error")
    else:
        flash("Post publicado com sucesso.", "success")
    return redirect(url_for("index"))


@app.post("/feed")
def fetch_feed():
    username = request.form.get("username", "").strip()
    limit_raw = request.form.get("limit", "25").strip()

    if not username:
        flash("Informe o usuário para consultar o feed.", "error")
        return redirect(url_for("index"))

    try:
        limit = int(limit_raw)
    except ValueError:
        limit = 25

    feed: Optional[List[dict]] = None
    try:
        with get_client() as client:
            feed = service.fetch_feed(client, username, limit=limit)
    except Exception as exc:  # pragma: no cover - feedback ao usuário
        flash(f"Erro ao buscar feed: {exc}", "error")
        return redirect(url_for("index"))

    return render_template("index.html", feed=feed, feed_username=username, feed_limit=limit)


if __name__ == "__main__":
    app.run(debug=True)
