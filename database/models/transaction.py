"""
database/models/transaction.py — Core financial transaction record.

Each row represents a single income or expense event.
All monetary values are stored in cents (integer) to avoid float rounding issues.
Display layer divides by 100 to show dollars/euros etc.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base
from database.models.category import CategoryType


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Income or expense
    type: Mapped[CategoryType] = mapped_column(
        Enum(CategoryType, name="category_type"),
        nullable=False,
    )

    # Amount in cents — e.g. $12.50 → 1250
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    # Human-readable description / reason
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # FK to category
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    category_rel: Mapped["Category"] = relationship("Category", back_populates="transactions")  # type: ignore

    # FK to user who created this record
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    creator: Mapped["User"] = relationship("User", back_populates="transactions")  # type: ignore

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Soft-delete — never physically remove rows for audit trail
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def amount(self) -> float:
        """Return dollar amount as float for display."""
        return self.amount_cents / 100

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} type={self.type} "
            f"amount=${self.amount:.2f} category={self.category_id}>"
        )
