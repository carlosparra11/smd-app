"""Storing transactions: importing a CSV file into the database, reading and adding."""

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ledger.db import Account, TransactionRow
from ledger.models import Transaction


def find_account(session: Session, name: str) -> Account | None:
    """The account called `name`, or None if there is none."""
    return session.scalars(select(Account).where(Account.name == name)).one_or_none()


def get_or_create_account(session: Session, name: str) -> Account:
    """The account called `name`, created (not yet committed) if it does not exist."""
    account = find_account(session, name)
    if account is None:
        account = Account(name=name)
        session.add(account)
        session.flush()
    return account


def import_csv(session: Session, path: Path) -> int:
    """Adds every row of a CSV file to the database. Returns how many were added.

    One commit at the end: either the whole file is imported or nothing is.
    """
    count = 0
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            session.add(
                TransactionRow(
                    date=date.fromisoformat(row["date"]),
                    account=get_or_create_account(session, row["account"]),
                    description=row["description"],
                    category=row["category"],
                    amount=Decimal(row["amount"]),
                )
            )
            count += 1
    session.commit()
    return count


def load_transactions(session: Session) -> list[Transaction]:
    """All the transactions in the database, by date."""
    rows = session.scalars(
        select(TransactionRow).order_by(TransactionRow.date, TransactionRow.id)
    ).all()
    return [
        Transaction(
            date=row.date,
            account=row.account.name,
            description=row.description,
            category=row.category,
            amount=row.amount,
        )
        for row in rows
    ]


def add_transaction(
    session: Session,
    account_name: str,
    amount: Decimal,
    category: str,
    description: str,
    day: date,
) -> None:
    """Records one transaction in an existing account."""
    account = find_account(session, account_name)
    if account is None:
        raise ValueError(f"no account called {account_name!r}")
    if amount != round(amount, 2):
        raise ValueError(f"amount {amount!r} is not a whole number of cents")
    session.add(
        TransactionRow(
            date=day,
            account=account,
            description=description,
            category=category,
            amount=amount,
        )
    )
    session.commit()
