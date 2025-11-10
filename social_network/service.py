"""Domain logic for the simple social network."""
from __future__ import annotations

from typing import Dict, List

from .neo4j_client import Neo4jClient


def create_user(client: Neo4jClient, username: str, name: str, bio: str = "") -> Dict:
    """Create or update a user profile."""
    result = client.execute_write(
        """
        MERGE (u:User {username: $username})
        ON CREATE SET u.created_at = datetime()
        SET u.name = $name,
            u.bio = $bio
        RETURN u { .* } AS user
        """,
        username=username,
        name=name,
        bio=bio,
    )
    if not result["records"]:
        raise RuntimeError("Falha ao criar ou atualizar o usuário.")
    return result["records"][0]["user"]


def add_follow(client: Neo4jClient, username: str, follows: str) -> None:
    """Create a `FOLLOWS` relationship between two users."""
    result = client.execute_write(
        """
        MATCH (source:User {username: $username})
        MATCH (target:User {username: $follows})
        MERGE (source)-[r:FOLLOWS]->(target)
        SET r.since = coalesce(r.since, date())
        RETURN source.username AS source, target.username AS target
        """,
        username=username,
        follows=follows,
    )
    if not result["records"]:
        raise ValueError("Usuário(s) não encontrado(s) para criar a relação de follow.")


def list_following(client: Neo4jClient, username: str) -> List[Dict]:
    """List the accounts a user follows."""
    records = client.execute_read(
        """
        MATCH (:User {username: $username})-[:FOLLOWS]->(friend:User)
        RETURN friend.username AS username,
               friend.name AS name,
               friend.bio AS bio
        ORDER BY friend.username
        """,
        username=username,
    )
    return list(records)


def create_post(client: Neo4jClient, username: str, content: str) -> Dict:
    """Create a new post for a user."""
    result = client.execute_write(
        """
        MATCH (author:User {username: $username})
        CREATE (author)-[:PUBLISHED]->(post:Post {
            id: randomUUID(),
            content: $content,
            created_at: datetime()
        })
        RETURN post { .* } AS post
        """,
        username=username,
        content=content,
    )
    if not result["records"]:
        raise ValueError("Usuário não encontrado para criar o post.")
    return result["records"][0]["post"]


def fetch_feed(client: Neo4jClient, username: str, limit: int = 25) -> List[Dict]:
    """Return recent posts from a user and the accounts they follow."""
    records = client.execute_read(
        """
        MATCH (viewer:User {username: $username})
        OPTIONAL MATCH (viewer)-[:FOLLOWS]->(followed:User)
        WITH viewer, collect(followed) + viewer AS authors
        UNWIND authors AS author
        MATCH (author)-[:PUBLISHED]->(post:Post)
        RETURN author.username AS username,
               author.name AS name,
               post.content AS content,
               post.created_at AS created_at
        ORDER BY post.created_at DESC
        LIMIT $limit
        """,
        username=username,
        limit=limit,
    )
    feed = list(records)
    if not feed:
        # If the viewer exists but has no posts in their feed the query still returns
        # zero rows. Check explicitly whether the viewer is present to return an empty
        # feed without raising.
        viewer_records = list(
            client.execute_read(
                "MATCH (viewer:User {username: $username}) RETURN viewer.username AS username",
                username=username,
            )
        )
        if not viewer_records:
            raise ValueError("Usuário não encontrado para consultar o feed.")
    return feed
