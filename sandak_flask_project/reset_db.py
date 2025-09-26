from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

from app import create_app, db
from app.models import User


def resolve_sqlite_path(database_uri: str) -> Path | None:
    """Return filesystem path for a sqlite URI, else None."""
    if not database_uri:
        return None
    if database_uri.startswith("sqlite:///"):
        return Path(database_uri.replace("sqlite:///", "")).resolve()
    if database_uri.startswith("sqlite:"):
        # Handles relative sqlite paths like sqlite:////absolute or sqlite:///relative
        parsed = urlparse(database_uri)
        if parsed.path:
            return Path(parsed.path).resolve()
    return None


def reset_database(username: str, email: str, password: str, role: str = "admin") -> None:
    app = create_app()
    with app.app_context():
        database_uri = app.config.get("SQLALCHEMY_DATABASE_URI")

        sqlite_path = resolve_sqlite_path(database_uri)
        if sqlite_path:
            if sqlite_path.exists():
                sqlite_path.unlink()
        else:
            # Fallback for non-sqlite: drop all tables
            db.drop_all()

        db.create_all()

        existing = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing:
            # If a record exists (edge case after drop_all fallback), clean slate
            db.session.delete(existing)
            db.session.commit()

        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        created_id = user.id
        location = str(sqlite_path) if sqlite_path else database_uri
        print(f"Database reset complete. New user created with id={created_id}. DB: {location}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset the database and create an initial user.")
    parser.add_argument("--username", default="admin", help="Username for the initial user (default: admin)")
    parser.add_argument("--email", default="admin@example.com", help="Email for the initial user (default: admin@example.com)")
    parser.add_argument(
        "--password",
        default="admin123",
        help="Password for the initial user (default: admin123)",
    )
    parser.add_argument("--role", default="admin", help="Role for the initial user (default: admin)")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    reset_database(args.username, args.email, args.password, args.role)

