"""
Database configuration and session management for HashVote.
"""

from sqlmodel import SQLModel, create_engine, Session
from typing import Generator


# SQLite database file path
DATABASE_URL = "sqlite:///./hashvote.db"

# Create engine with SQLite-specific settings
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging during development
    connect_args={
        "check_same_thread": False
    },  # Allow sharing connections between threads
)


def create_db_and_tables():
    """
    Create the database and all tables.

    This should be called when the application starts.
    """
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """
    Dependency to get a database session.

    Yields:
        Database session instance
    """
    with Session(engine) as session:
        yield session


def get_session_direct() -> Session:
    """
    Get a direct database session for CLI usage.

    Returns:
        Database session instance
    """
    return Session(engine)
