"""End-to-end integration tests for RAG Conversational Engine"""
import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# Load .env
env_path = Path(".env")
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        value = value.split("#")[0].strip()
        if key:
            os.environ[key] = value

# Set dummy API keys for testing
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("TAVILY_API_KEY", "test-key")


class TestResults:
    """Track test execution results"""
    def __init__(self):
        self.passed = []
        self.failed = []
        self.skipped = []
        self.start_time = datetime.utcnow()

    def add_pass(self, test_name: str, message: str = ""):
        self.passed.append({"name": test_name, "message": message})
        print(f"PASS: {test_name}")

    def add_fail(self, test_name: str, error: str):
        self.failed.append({"name": test_name, "error": error})
        print(f"FAIL: {test_name} - {error}")

    def add_skip(self, test_name: str, reason: str):
        self.skipped.append({"name": test_name, "reason": reason})
        print(f"SKIP: {test_name} - {reason}")

    def summary(self) -> dict:
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        total = len(self.passed) + len(self.failed) + len(self.skipped)
        return {
            "total": total,
            "passed": len(self.passed),
            "failed": len(self.failed),
            "skipped": len(self.skipped),
            "elapsed_seconds": elapsed,
            "success_rate": len(self.passed) / max(total, 1),
        }


results = TestResults()


async def test_imports():
    """Test all system imports"""
    try:
        from app.main import init_session_state
        from app.integration import run_eira_agent
        from app.components import render_response_card
        from app.wire_tools import wire_all_tools
        from agent_definitions.eira import EIRA
        from models.pydantic_io import EIRAResponse
        from tools import (
            execute_employee_query,
            search_weather_embeddings,
            search_news_embeddings,
        )
        results.add_pass("test_imports", "All modules import successfully")
    except Exception as e:
        results.add_fail("test_imports", str(e))
        return False
    return True


async def test_wire_tools():
    """Test tool wiring"""
    try:
        from app.wire_tools import wire_all_tools
        from agent_definitions.eira import EIRA

        wire_all_tools()

        # Verify EIRA has tools
        if not EIRA.tools:
            raise ValueError("EIRA.tools is empty after wiring")

        # Verify EIRA has handoffs
        if not EIRA.handoffs:
            raise ValueError("EIRA.handoffs is empty after wiring")

        results.add_pass(
            "test_wire_tools",
            f"Wired {len(EIRA.tools)} tools + {len(EIRA.handoffs)} handoffs",
        )
    except Exception as e:
        results.add_fail("test_wire_tools", str(e))
        return False
    return True


async def test_sql_query_execution():
    """Test 6A: SQL-only queries (VEGA path)"""
    try:
        from tools.sql_tools import execute_employee_query
        from db.engine import get_db_session
        from models.employee import Employee

        # Check if employee data exists
        with get_db_session() as session:
            count = session.query(Employee).count()
            if count == 0:
                results.add_skip(
                    "test_sql_query_execution",
                    "No employee data (run init_databases.py)",
                )
                return True

        # Test simple query
        result = await execute_employee_query(department="Engineering")
        if not result.get("employees"):
            raise ValueError("No engineers found")

        results.add_pass(
            "test_sql_query_execution",
            f"Found {len(result['employees'])} engineers",
        )
    except Exception as e:
        results.add_fail("test_sql_query_execution", str(e))
        return False
    return True


async def test_chroma_validation():
    """Test 6B: Chroma location contract validation"""
    try:
        from tools.chroma_tools import validate_location_contract

        # Test valid chunks
        valid_chunks = [
            {
                "id": "chunk1",
                "text": "Weather in Austin",
                "metadata": {"location_normalized": "Austin, TX"},
            },
        ]

        result = await validate_location_contract(valid_chunks)
        if not result.get("is_valid"):
            raise ValueError(f"Validation failed: {result.get('violations')}")

        results.add_pass("test_chroma_validation", "Location contract validation passed")
    except Exception as e:
        results.add_fail("test_chroma_validation", str(e))
        return False
    return True


async def test_sql_injection_blocking():
    """Test 6D: AXIOM blocks SQL injection"""
    try:
        from tools.sql_tools import validate_sql_query

        malicious_sql = "SELECT * FROM employees UNION SELECT * FROM users"
        result = await validate_sql_query(malicious_sql)

        # result is a ValidationResult object, not a dict
        if not result.is_blocked:
            raise ValueError("SQL injection not blocked")

        results.add_pass(
            "test_sql_injection_blocking",
            "SQL injection correctly blocked",
        )
    except Exception as e:
        results.add_fail("test_sql_injection_blocking", str(e))
        return False
    return True


async def test_embedding_generation():
    """Test 6B: Embedding generation"""
    try:
        from tools.embedding_tools import generate_embeddings

        texts = ["Weather in Austin", "Tech news"]
        result = generate_embeddings(texts)

        if not result.get("success"):
            error = result.get('error', '')
            if '401' in error or 'API key' in error:
                results.add_skip("test_embedding_generation", "OpenAI API key invalid")
                return True
            raise ValueError(f"Embedding failed: {error}")

        if len(result.get("embeddings", [])) != 2:
            raise ValueError("Wrong number of embeddings")

        results.add_pass(
            "test_embedding_generation",
            "Generated 2 embeddings",
        )
    except Exception as e:
        results.add_fail("test_embedding_generation", str(e))
        return False
    return True


async def test_pii_detection():
    """Test 6E: PII detection in hooks"""
    try:
        from hooks.preprocessing import check_pii_leakage

        # Test with fake SSN
        tool_args = {"employee_id": "123-45-6789"}
        result = await check_pii_leakage("test_tool", tool_args)

        if not result.get("has_pii"):
            raise ValueError("SSN not detected as PII")

        results.add_pass("test_pii_detection", "PII detection working")
    except Exception as e:
        results.add_fail("test_pii_detection", str(e))
        return False
    return True


async def test_database_connectivity():
    """Test 2: Database connectivity"""
    try:
        from db.engine import get_db_session
        from models.employee import Employee

        with get_db_session() as session:
            count = session.query(Employee).count()

        results.add_pass("test_database_connectivity", f"Database connected ({count} employees)")
    except Exception as e:
        results.add_fail("test_database_connectivity", str(e))
        return False
    return True


async def test_chroma_connectivity():
    """Test 2: Chroma connectivity"""
    try:
        from chroma.client import get_chroma_client

        client = get_chroma_client()
        if not client:
            raise ValueError("Chroma client not initialized")

        results.add_pass("test_chroma_connectivity", "Chroma connected")
    except Exception as e:
        results.add_fail("test_chroma_connectivity", str(e))
        return False
    return True


async def run_all_tests():
    """Execute all tests"""
    print("=" * 60)
    print("RAG CONVERSATIONAL ENGINE - E2E TEST SUITE")
    print("=" * 60)
    print()

    # Initialize databases
    print("Initializing databases...")
    try:
        from db.engine import init_db
        from chroma.client import init_chroma
        init_db()
        init_chroma()
        print("Databases initialized")
    except Exception as e:
        print(f"Warning: Database init failed: {e}")
    print()

    print("System Imports & Setup")
    print("-" * 60)
    await test_imports()
    await test_database_connectivity()
    await test_chroma_connectivity()
    await test_wire_tools()
    print()

    print("Phase 6A: SQL-Only Queries (VEGA)")
    print("-" * 60)
    await test_sql_query_execution()
    await test_sql_injection_blocking()
    print()

    print("Phase 6B: RAG Queries (NOVA)")
    print("-" * 60)
    await test_chroma_validation()
    await test_embedding_generation()
    print()

    print("Phase 6E: Hooks & Security")
    print("-" * 60)
    await test_pii_detection()
    print()

    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    summary = results.summary()
    print(f"Total:    {summary['total']}")
    print(f"Passed:   {summary['passed']}")
    print(f"Failed:   {summary['failed']}")
    print(f"Skipped:  {summary['skipped']}")
    print(f"Success Rate: {summary['success_rate']:.1%}")
    print()

    if summary["failed"] == 0:
        print("ALL TESTS PASSED")
        return 0
    else:
        print(f"{summary['failed']} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
