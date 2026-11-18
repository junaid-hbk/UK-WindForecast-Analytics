"""Repository layer: all SQL lives here.

Conventions:

* repositories never commit; the caller owns the transaction boundary;
* repositories never contain business rules (no cutoffs, no metric definitions);
* every write is expressed so that repeating it is safe.
"""

from __future__ import annotations

from sqlalchemy.orm import Session


class BaseRepository:
    """Base class holding the unit-of-work session."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def flush(self) -> None:
        """Send pending statements to the database without committing."""
        self.session.flush()
