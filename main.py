"""Command-line interface for the Neo4j social network demo."""
from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
from typing import Iterator

from social_network.neo4j_client import Neo4jClient
from social_network import service


@contextmanager
def get_client() -> Iterator[Neo4jClient]:
    client = Neo4jClient()
    try:
        yield client
    finally:
        client.close()


def handle_create_user(args: argparse.Namespace) -> None:
    with get_client() as client:
        user = service.create_user(client, args.username, args.name, args.bio or "")
    print(json.dumps(user, default=str, indent=2))


def handle_follow(args: argparse.Namespace) -> None:
    with get_client() as client:
        service.add_follow(client, args.username, args.follows)
    print(json.dumps({"status": "ok"}))


def handle_list_following(args: argparse.Namespace) -> None:
    with get_client() as client:
        following = service.list_following(client, args.username)
    print(json.dumps(following, default=str, indent=2))


def handle_create_post(args: argparse.Namespace) -> None:
    with get_client() as client:
        post = service.create_post(client, args.username, args.content)
    print(json.dumps(post, default=str, indent=2))


def handle_feed(args: argparse.Namespace) -> None:
    with get_client() as client:
        feed = service.fetch_feed(client, args.username, args.limit)
    print(json.dumps(feed, default=str, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Neo4j social network demo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_user_parser = subparsers.add_parser("create-user", help="Create or update a user profile")
    create_user_parser.add_argument("username", help="Unique username for the user")
    create_user_parser.add_argument("name", help="Display name for the user")
    create_user_parser.add_argument("--bio", help="Short biography", default="")
    create_user_parser.set_defaults(func=handle_create_user)

    follow_parser = subparsers.add_parser("follow", help="Follow another user")
    follow_parser.add_argument("username", help="Account that will follow someone")
    follow_parser.add_argument("follows", help="Account to follow")
    follow_parser.set_defaults(func=handle_follow)

    list_following_parser = subparsers.add_parser("list-following", help="List who a user follows")
    list_following_parser.add_argument("username", help="Account to inspect")
    list_following_parser.set_defaults(func=handle_list_following)

    create_post_parser = subparsers.add_parser("create-post", help="Create a post for a user")
    create_post_parser.add_argument("username", help="Author of the post")
    create_post_parser.add_argument("content", help="Post content")
    create_post_parser.set_defaults(func=handle_create_post)

    feed_parser = subparsers.add_parser("feed", help="Fetch a user feed")
    feed_parser.add_argument("username", help="Viewer of the feed")
    feed_parser.add_argument("--limit", type=int, default=25, help="Maximum number of posts to return")
    feed_parser.set_defaults(func=handle_feed)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
