"""
database/models/category.py — Transaction categories.

Categories are typed (income / expense) so the UI can filter
relevant options when adding a transaction.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base
import enum


class CategoryType(str, enum.Enum):
    income = "income"
    expense = "expense"


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    type: Mapped[CategoryType] = mapped_column(
        Enum(CategoryType, name="category_type"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationship — category → many transactions
    transactions: Mapped[list] = relationship("Transaction", back_populates="category_rel", lazy="select")

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name} type={self.type}>"
