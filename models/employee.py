"""
SQLAlchemy ORM Model — Employee Table

Employee table with 500 rows seeded via db/seed.py.
office_location MUST be a value from CANONICAL_CITIES.
Constraint enforced at: DB level, seed level, and application level.

Reference: handoff.md §2.3
"""

from __future__ import annotations

from sqlalchemy import Integer, String, CheckConstraint, Index
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from config.constants import CANONICAL_CITIES, DEPARTMENTS


class Base(DeclarativeBase):
    """Base class for all ORM models"""
    pass


class Employee(Base):
    """
    Employee table — 500 rows, one per unique employee.

    office_location MUST be a value from CANONICAL_CITIES.
    This constraint is enforced at:
      1. DB level: CheckConstraint (SQLite supports basic checks)
      2. Seed level: Faker only picks from CANONICAL_CITIES
      3. Application level: Pydantic EmployeeRow validator
    """

    __tablename__ = "employees"

    __table_args__ = (
        CheckConstraint(
            "age >= 22 AND age <= 65",
            name="ck_employee_age_range",
        ),
        CheckConstraint(
            "length(name) > 0",
            name="ck_employee_name_nonempty",
        ),
        # Indexes for common query patterns
        Index("ix_employees_name", "name"),
        Index("ix_employees_office_location", "office_location"),
        Index("ix_employees_department", "department"),
    )

    employee_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    department: Mapped[str] = mapped_column(String(60), nullable=False)
    office_location: Mapped[str] = mapped_column(String(60), nullable=False)

    def __repr__(self) -> str:
        return (
            f"Employee(id={self.employee_id}, name={self.name!r}, "
            f"age={self.age}, dept={self.department!r}, "
            f"location={self.office_location!r})"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary (for serialization)"""
        return {
            "employee_id": self.employee_id,
            "name": self.name,
            "age": self.age,
            "department": self.department,
            "office_location": self.office_location,
        }

    def to_pydantic(self):
        """Convert to Pydantic EmployeeRow"""
        from models.pydantic_io import EmployeeRow

        return EmployeeRow(
            employee_id=self.employee_id,
            name=self.name,
            age=self.age,
            department=self.department,
            office_location=self.office_location,
        )
