"""The database: the tables, how money is stored, and how to open a session."""

from datetime import date
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, String, create_engine, event
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
)
from sqlalchemy.types import TypeDecorator

DATABASE_URL = "sqlite:///ledger.db"


class Money(TypeDecorator):
    """Stores a `Decimal` amount as a whole number of cents, never as a float."""

    impl = Integer
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return int(Decimal(value) * 100)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return Decimal(value).scaleb(-2)


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    rows: Mapped[list[TransactionRow]] = relationship(back_populates="account")


class TransactionRow(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date]
    description: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))
    amount: Mapped[Decimal] = mapped_column(Money)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    account: Mapped[Account] = relationship(back_populates="rows")


engine = create_engine(DATABASE_URL)


@event.listens_for(engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record) -> None:
    """SQLite only checks foreign keys when asked to, once per connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_tables() -> None:
    """Creates the tables that do not exist yet. Existing data is kept."""
    Base.metadata.create_all(engine)


def get_session() -> Session:
    """A new session to read and write the database."""
    return Session(engine)
