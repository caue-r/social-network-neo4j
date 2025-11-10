"""Utility helpers for working with Neo4j."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from neo4j import GraphDatabase, Driver
from neo4j.exceptions import Neo4jError
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Neo4jConfig:
    uri: str
    username: str
    password: str
    database: Optional[str] = None

    @classmethod
    def from_environment(cls) -> "Neo4jConfig":
        """Build a configuration from standard environment variables."""
        uri = os.getenv("NEO4J_URI")
        username = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")
        database = os.getenv("NEO4J_DATABASE")

        missing = [name for name, value in {
            "NEO4J_URI": uri,
            "NEO4J_USERNAME": username,
            "NEO4J_PASSWORD": password,
        }.items() if not value]
        if missing:
            missing_str = ", ".join(missing)
            raise RuntimeError(
                f"Missing required environment variables for Neo4j connection: {missing_str}"
            )

        return cls(uri=uri, username=username, password=password, database=database)


class Neo4jClient:
    """A small wrapper around the official Neo4j Python driver."""

    def __init__(self, config: Optional[Neo4jConfig] = None) -> None:
        self.config = config or Neo4jConfig.from_environment()
        self.driver: Driver = GraphDatabase.driver(
            self.config.uri,
            auth=(self.config.username, self.config.password),
        )

    def close(self) -> None:
        self.driver.close()

    def execute_write(self, query: str, **parameters: Any) -> Dict[str, Any]:
        """Execute a write query and return the records and summary."""

        def work(tx) -> Dict[str, Any]:
            result = tx.run(query, **parameters)
            records = [dict(record) for record in result]
            summary = result.consume()
            counters = summary.counters
            summary_dict = {
                "nodes_created": counters.nodes_created,
                "nodes_deleted": counters.nodes_deleted,
                "relationships_created": counters.relationships_created,
                "relationships_deleted": counters.relationships_deleted,
                "properties_set": counters.properties_set,
            }
            return {"records": records, "summary": summary_dict}

        return self._run(lambda session: session.execute_write(work))

    def execute_read(self, query: str, **parameters: Any) -> Iterable[Dict[str, Any]]:
        """Execute a read-only query and return the records as dictionaries."""

        def work(tx) -> Iterable[Dict[str, Any]]:
            result = tx.run(query, **parameters)
            return [dict(record) for record in result]

        return self._run(lambda session: session.execute_read(work))

    def _run(self, callback) -> Any:
        database = self.config.database
        session_kwargs = {"database": database} if database else {}
        try:
            with self.driver.session(**session_kwargs) as session:
                return callback(session)
        except Neo4jError as exc:  # pragma: no cover - defensive programming
            raise RuntimeError("Neo4j query failed") from exc
