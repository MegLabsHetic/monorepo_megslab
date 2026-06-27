"""Colonnes communes a tous les modeles : identifiant et horodatage."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


def _id_par_defaut() -> str:
    return uuid.uuid4().hex


def _maintenant() -> datetime:
    return datetime.now(UTC)


class HorodatageMixin:
    """id en uuid (texte, portable entre bases) et dates de creation/maj."""

    id: Mapped[str] = mapped_column(primary_key=True, default=_id_par_defaut)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_maintenant)
    maj_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_maintenant, onupdate=_maintenant
    )
