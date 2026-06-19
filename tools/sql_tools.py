"""SQL tools for VEGA agent"""
from typing import Any
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from models.pydantic_io import ValidationResult, EmployeeRow
from db.engine import get_db_session
from models.employee import Employee


async def get_schema_snapshot() -> dict[str, Any]:
    """Return live schema snapshot for AXIOM inspection"""
    with get_db_session() as session:
        inspector = inspect(session.bind)
        columns = inspector.get_columns("employees")
        return {
            "table": "employees",
            "columns": [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col["nullable"],
                }
                for col in columns
            ],
        }


async def validate_sql_query(sql_string: str) -> ValidationResult:
    """Validate SQL query via AXIOM before execution"""
    # Pattern detection for common SQL injection vectors
    dangerous_patterns = [
        "UNION",
        "DROP",
        "INSERT",
        "DELETE",
        "UPDATE",
        "TRUNCATE",
        "ALTER",
        "--",
        ";",
        "/*",
        "*/",
        "xp_",
        "sp_",
    ]

    upper_sql = sql_string.upper()
    issues = []

    for pattern in dangerous_patterns:
        if pattern in upper_sql:
            issues.append(f"Detected dangerous pattern: {pattern}")

    if "SELECT *" in upper_sql:
        issues.append("SELECT * not allowed; specify columns")

    if issues:
        return ValidationResult(
            is_valid=False,
            is_blocked=True,
            issues=issues,
            safe_to_execute=False,
            query_type="sql",
        )

    return ValidationResult(
        is_valid=True,
        is_blocked=False,
        issues=[],
        safe_to_execute=True,
        query_type="sql",
    )


async def execute_employee_query(
    name: str | None = None,
    department: str | None = None,
    office_location: str | None = None,
    age_min: int | None = None,
    age_max: int | None = None,
) -> dict[str, Any]:
    """Execute parameterized employee query"""
    try:
        with get_db_session() as session:
            query = session.query(Employee)

            if name:
                query = query.filter(Employee.name.ilike(f"%{name}%"))
            if department:
                query = query.filter(Employee.department == department)
            if office_location:
                query = query.filter(
                    Employee.office_location == office_location
                )
            if age_min is not None:
                query = query.filter(Employee.age >= age_min)
            if age_max is not None:
                query = query.filter(Employee.age <= age_max)

            rows = query.all()
            employees = [EmployeeRow(**row.to_dict()) for row in rows]

            # Generate SQL string for audit
            sql_str = str(query.statement.compile(compile_kwargs={"literal_binds": True}))

            return {
                "employees": [emp.model_dump() for emp in employees],
                "query_sql": sql_str,
                "row_count": len(employees),
                "ambiguous_match": len(employees) > 1 and name is not None,
            }
    except SQLAlchemyError as e:
        return {
            "employees": [],
            "query_sql": "",
            "row_count": 0,
            "error": str(e),
        }
