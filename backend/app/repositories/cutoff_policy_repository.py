"""Cutoff policy access."""

from __future__ import annotations

from sqlalchemy import select

from app.core.errors import NotFoundError
from app.models.cutoff import CutoffPolicy
from app.repositories.base import BaseRepository


class CutoffPolicyRepository(BaseRepository):
    """Read access to the configurable day-ahead cutoff policies."""

    def list_all(self) -> list[CutoffPolicy]:
        """Return every policy, default first."""
        stmt = select(CutoffPolicy).order_by(
            CutoffPolicy.is_default.desc(), CutoffPolicy.local_time.asc()
        )
        return list(self.session.scalars(stmt))

    def get_by_code(self, code: str) -> CutoffPolicy:
        """Return a policy by code or raise ``NotFoundError``."""
        stmt = select(CutoffPolicy).where(CutoffPolicy.code == code)
        policy = self.session.scalars(stmt).one_or_none()
        if policy is None:
            raise NotFoundError(
                f"Unknown cutoff policy {code!r}",
                details={"available": [p.code for p in self.list_all()]},
            )
        return policy

    def get_default(self) -> CutoffPolicy:
        """Return the policy flagged as default, else the earliest one."""
        stmt = select(CutoffPolicy).where(CutoffPolicy.is_default.is_(True))
        policy = self.session.scalars(stmt).first()
        if policy is not None:
            return policy
        stmt = select(CutoffPolicy).order_by(CutoffPolicy.local_time.asc())
        policy = self.session.scalars(stmt).first()
        if policy is None:
            raise NotFoundError("No cutoff policies are configured")
        return policy

    def resolve(self, code: str | None) -> CutoffPolicy:
        """Resolve an optional code to a policy, falling back to the default."""
        return self.get_default() if code is None else self.get_by_code(code)
