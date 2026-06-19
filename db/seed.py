"""
Seed Script — Generate 500 Employee Rows

Deterministic seed with fixed Faker seed, balanced across:
  - 10 canonical cities (~50 rows each, ±10 for realism)
  - 8 departments (weighted toward Engineering/Sales)
  - Ages 22–65 (triangular distribution, mode ~38)

Safe to re-run: clears existing rows before inserting.

Reference: handoff.md §2.4
"""

import random
from faker import Faker
from sqlalchemy.orm import Session
from sqlalchemy import func

from db.engine import get_sync_engine, init_db
from models.employee import Employee, Base
from config.constants import CANONICAL_CITIES, DEPARTMENTS
from loguru import logger

# ── Seed Configuration ───────────────────────────────────────────────
FAKER_SEED = 42  # Fixed seed → reproducible dataset across all runs
TOTAL_ROWS = 500

# Department weights (sum to 1.0) — Engineering and Sales are largest
DEPT_WEIGHTS = [0.25, 0.20, 0.10, 0.10, 0.10, 0.10, 0.10, 0.05]
assert len(DEPT_WEIGHTS) == len(DEPARTMENTS)
assert abs(sum(DEPT_WEIGHTS) - 1.0) < 1e-9

# City distribution: roughly equal with slight randomness
CITY_WEIGHTS = [0.12, 0.12, 0.14, 0.10, 0.09, 0.09, 0.10, 0.08, 0.08, 0.08]
assert len(CITY_WEIGHTS) == len(CANONICAL_CITIES)
assert abs(sum(CITY_WEIGHTS) - 1.0) < 1e-9


def generate_employees(n: int = TOTAL_ROWS) -> list[Employee]:
    """Generate n deterministic employees using Faker."""
    fake = Faker("en_US")
    Faker.seed(FAKER_SEED)
    random.seed(FAKER_SEED)

    employees = []
    for _ in range(n):
        # Age: triangular distribution skewed toward mid-career (35–45)
        age = int(random.triangular(22, 65, 38))
        age = max(22, min(65, age))  # clamp to valid range

        employees.append(
            Employee(
                name=fake.name(),
                age=age,
                department=random.choices(DEPARTMENTS, weights=DEPT_WEIGHTS, k=1)[0],
                office_location=random.choices(CANONICAL_CITIES, weights=CITY_WEIGHTS, k=1)[0],
            )
        )

    return employees


def run_seed(clear_existing: bool = True):
    """
    Main seed entry point.

    Args:
        clear_existing: If True, deletes all existing employee rows first.
                        Safe default for development.
    """
    init_db()
    engine = get_sync_engine()

    with Session(engine) as session:
        if clear_existing:
            deleted = session.query(Employee).delete()
            session.commit()
            logger.info(f"Cleared {deleted} existing employee rows.")

        employees = generate_employees(TOTAL_ROWS)

        # Chunked insert: 100 rows per flush for memory efficiency
        chunk_size = 100
        for i in range(0, len(employees), chunk_size):
            chunk = employees[i : i + chunk_size]
            session.add_all(chunk)
            session.flush()
            logger.debug(f"Flushed rows {i}–{i + len(chunk) - 1}")

        session.commit()
        logger.info(f"Seeded {TOTAL_ROWS} employee rows.")

        # ── Verification Report ──────────────────────────────────────
        total = session.query(Employee).count()
        logger.info(f"Total rows in DB: {total}")

        # City distribution
        logger.info("City distribution:")
        city_counts = (
            session.query(Employee.office_location, func.count(Employee.employee_id))
            .group_by(Employee.office_location)
            .all()
        )
        for city, count in sorted(city_counts):
            logger.info(f"  {city:<20} → {count:3d} employees")

        # Department distribution
        logger.info("Department distribution:")
        dept_counts = (
            session.query(Employee.department, func.count(Employee.employee_id))
            .group_by(Employee.department)
            .all()
        )
        for dept, count in sorted(dept_counts):
            logger.info(f"  {dept:<22} → {count:3d} employees")

        # Age statistics
        logger.info("Age statistics:")
        ages = session.query(Employee.age).all()
        ages_list = [age[0] for age in ages]
        logger.info(f"  Min: {min(ages_list)}, Max: {max(ages_list)}, Avg: {sum(ages_list)/len(ages_list):.1f}")


if __name__ == "__main__":
    run_seed()
