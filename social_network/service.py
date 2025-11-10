"""Domain logic for the simple social network."""
from __future__ import annotations

from typing import Dict, List, Optional

from .neo4j_client import Neo4jClient


def create_user(client: Neo4jClient, username: str, name: str, bio: str = "") -> Dict:
    """Create or update a user profile."""
    result = client.execute_write(
        """
        MERGE (u:User {username: $username})
        ON CREATE SET u.created_at = datetime()
        SET u.name = $name,
            u.bio = $bio,
            u.username_lower = toLower($username)
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


def remove_follow(client: Neo4jClient, username: str, unfollow: str) -> None:
    """Remove a FOLLOWS relationship between two users."""
    result = client.execute_write(
        """
        MATCH (source:User {username: $username})-[r:FOLLOWS]->(target:User {username: $unfollow})
        DELETE r
        RETURN source.username AS source, target.username AS target
        """,
        username=username,
        unfollow=unfollow,
    )
    if not result["records"]:
        raise ValueError("Relacionamento de follow não encontrado.")


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


def register_account(
    client: Neo4jClient,
    *,
    name: str,
    email: str,
    username: str,
    password_hash: str,
) -> Dict:
    """Register a brand-new user enforcing unique username/email."""
    conflicts = list(
        client.execute_read(
            """
            MATCH (u:User)
            WHERE toLower(u.username) = $username_lower
               OR toLower(coalesce(u.email, '')) = $email_lower
            RETURN u.username AS username, u.email AS email
            LIMIT 1
            """,
            username_lower=username.lower(),
            email_lower=email.lower(),
        )
    )
    if conflicts:
        raise ValueError("Já existe um usuário cadastrado com este usuário ou email.")

    result = client.execute_write(
        """
        CREATE (u:User {
            id: randomUUID(),
            username: $username,
            username_lower: toLower($username),
            name: $name,
            email: $email,
            email_lower: toLower($email),
            password_hash: $password_hash,
            created_at: datetime()
        })
        RETURN u { .* } AS user
        """,
        username=username,
        name=name,
        email=email,
        password_hash=password_hash,
    )
    if not result["records"]:
        raise RuntimeError("Não foi possível criar o usuário.")
    return result["records"][0]["user"]


def find_user_for_login(client: Neo4jClient, identifier: str) -> Optional[Dict]:
    """Fetch a user (including password hash) by username or email."""
    records = list(
        client.execute_read(
            """
            MATCH (u:User)
            WHERE toLower(u.username) = $identifier
               OR toLower(coalesce(u.email, '')) = $identifier
            RETURN u {
                .username,
                .name,
                .email,
                .password_hash
            } AS user
            LIMIT 1
            """,
            identifier=identifier.lower(),
        )
    )
    if not records:
        return None
    return records[0]["user"]


def search_users(
    client: Neo4jClient,
    query: str,
    *,
    limit: int = 20,
) -> List[Dict]:
    """Search public profiles by username or name."""
    needle = (query or "").strip().lower()
    if not needle:
        return []

    records = client.execute_read(
        """
        MATCH (u:User)
        WHERE toLower(u.username) CONTAINS $needle
           OR toLower(coalesce(u.name, '')) CONTAINS $needle
        RETURN u {
            .username,
            .name,
            .bio
        } AS user
        ORDER BY u.username
        LIMIT $limit
        """,
        needle=needle,
        limit=limit,
    )
    return [record["user"] for record in records]


def admin_search_users(
    client: Neo4jClient,
    query: str,
    *,
    limit: int = 50,
) -> List[Dict]:
    """Search for users by username, email, or name for the admin panel."""
    needle = (query or "").lower()
    records = client.execute_read(
        """
        MATCH (u:User)
        WHERE $needle = ''
           OR toLower(u.username) CONTAINS $needle
           OR toLower(coalesce(u.email, '')) CONTAINS $needle
           OR toLower(coalesce(u.name, '')) CONTAINS $needle
        RETURN u {
            .username,
            .name,
            .email,
            .bio,
            .created_at
        } AS user
        ORDER BY u.username
        LIMIT $limit
        """,
        needle=needle,
        limit=limit,
    )
    return [record["user"] for record in records]


def admin_create_user(
    client: Neo4jClient,
    *,
    username: str,
    password_hash: str,
    name: str = "",
    email: Optional[str] = None,
    bio: str = "",
) -> Dict:
    """Create a new user from the admin panel."""
    username_clean = username.strip()
    if not username_clean or not password_hash:
        raise ValueError("Usuário e senha são obrigatórios.")

    email_clean = email.strip() if email else None
    name_clean = name.strip() if name else ""
    bio_clean = bio.strip() if bio else ""
    _ensure_unique_identity(
        client,
        username_lower=username_clean.lower(),
        email_lower=email_clean.lower() if email_clean else None,
    )

    result = client.execute_write(
        """
        CREATE (u:User {
            id: randomUUID(),
            username: $username,
            username_lower: toLower($username),
            name: $name,
            email: $email,
            email_lower: CASE
                WHEN $email IS NULL OR $email = '' THEN NULL
                ELSE toLower($email)
            END,
            bio: $bio,
            password_hash: $password_hash,
            created_at: datetime()
        })
        RETURN u { .* } AS user
        """,
        username=username_clean,
        name=name_clean,
        email=email_clean,
        bio=bio_clean,
        password_hash=password_hash,
    )
    if not result["records"]:
        raise RuntimeError("Não foi possível criar o usuário.")
    return result["records"][0]["user"]


def admin_update_user(
    client: Neo4jClient,
    *,
    username: str,
    new_username: Optional[str] = None,
    name: Optional[str] = None,
    email: Optional[str] = None,
    bio: Optional[str] = None,
    password_hash: Optional[str] = None,
) -> Dict:
    """Update fields on a user from the admin panel."""
    if not username:
        raise ValueError("Usuário original é obrigatório.")

    if new_username and new_username != username:
        _ensure_unique_identity(
            client,
            username_lower=new_username.lower(),
            email_lower=None,
            exclude_username=username,
        )

    if email is not None:
        email_clean = email.strip() or None
        if email_clean:
            _ensure_unique_identity(
                client,
                username_lower=None,
                email_lower=email_clean.lower(),
                exclude_username=username,
            )
    else:
        email_clean = None

    set_clauses = []
    params = {"username": username}

    if new_username:
        params["new_username"] = new_username.strip()
        if not params["new_username"]:
            raise ValueError("O novo usuário não pode estar vazio.")
        params["new_username_lower"] = params["new_username"].lower()
        set_clauses.append("u.username = $new_username")
        set_clauses.append("u.username_lower = $new_username_lower")

    if name is not None:
        params["name"] = name.strip()
        set_clauses.append("u.name = $name")

    if email is not None:
        params["email"] = email_clean
        params["email_lower"] = email_clean.lower() if email_clean else None
        set_clauses.append("u.email = $email")
        set_clauses.append("u.email_lower = $email_lower")

    if bio is not None:
        params["bio"] = bio.strip()
        set_clauses.append("u.bio = $bio")

    if password_hash:
        params["password_hash"] = password_hash
        set_clauses.append("u.password_hash = $password_hash")

    if not set_clauses:
        raise ValueError("Nenhum campo para atualizar.")

    result = client.execute_write(
        f"""
        MATCH (u:User {{username: $username}})
        SET {', '.join(set_clauses)}
        RETURN u {{ .* }} AS user
        """,
        **params,
    )
    if not result["records"]:
        raise ValueError("Usuário não encontrado para atualização.")
    return result["records"][0]["user"]


def admin_delete_user(client: Neo4jClient, username: str) -> None:
    """Delete a user (and related nodes) from the admin panel."""
    if not username:
        raise ValueError("Usuário é obrigatório para exclusão.")
    result = client.execute_write(
        """
        MATCH (u:User {username: $username})
        OPTIONAL MATCH (u)-[:PUBLISHED]->(post:Post)
        DETACH DELETE u, post
        RETURN 1 AS deleted
        """,
        username=username,
    )
    if not result["records"]:
        raise ValueError("Usuário não encontrado para exclusão.")


def _ensure_unique_identity(
    client: Neo4jClient,
    *,
    username_lower: Optional[str],
    email_lower: Optional[str],
    exclude_username: Optional[str] = None,
) -> None:
    """Ensure username/email uniqueness when creating/updating users."""
    if username_lower:
        records = client.execute_read(
            """
            MATCH (u:User)
            WHERE toLower(u.username) = $username_lower
              AND ($exclude_username IS NULL OR u.username <> $exclude_username)
            RETURN u.username AS username
            LIMIT 1
            """,
            username_lower=username_lower,
            exclude_username=exclude_username,
        )
        if records:
            raise ValueError("Já existe um usuário com este username.")

    if email_lower:
        records = client.execute_read(
            """
            MATCH (u:User)
            WHERE toLower(coalesce(u.email, '')) = $email_lower
              AND ($exclude_username IS NULL OR u.username <> $exclude_username)
            RETURN u.username AS username
            LIMIT 1
            """,
            email_lower=email_lower,
            exclude_username=exclude_username,
        )
        if records:
            raise ValueError("Já existe um usuário com este email.")
