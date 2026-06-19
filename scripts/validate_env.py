#!/usr/bin/env python3
"""
Phase 0 Validation Script
Verifies environment setup, dependencies, and API connectivity
"""

import sys
import os
from pathlib import Path

# Fix encoding on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_python_version():
    """Verify Python 3.11+"""
    ver = sys.version_info
    if ver.major < 3 or (ver.major == 3 and ver.minor < 11):
        print(f"❌ Python 3.11+ required. Found: {ver.major}.{ver.minor}")
        return False
    print(f"✅ Python version: {ver.major}.{ver.minor}.{ver.micro}")
    return True


def check_venv():
    """Check if running in virtual environment"""
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    if in_venv:
        print(f"✅ Virtual environment active: {sys.prefix}")
        return True
    else:
        print("⚠️  Not in virtual environment (optional but recommended)")
        return True


def check_dependencies():
    """Verify core dependencies are importable"""
    required = [
        ("openai", "OpenAI SDK"),
        ("anthropic", "Anthropic SDK"),
        ("sqlalchemy", "SQLAlchemy ORM"),
        ("chromadb", "ChromaDB"),
        ("pydantic", "Pydantic"),
        ("streamlit", "Streamlit"),
        ("loguru", "Loguru"),
        ("dotenv", "python-dotenv"),
    ]

    all_ok = True
    for module, name in required:
        try:
            __import__(module)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name} — import failed. Run: uv install")
            all_ok = False

    return all_ok


def check_env_file():
    """Verify .env file exists and has required keys"""
    env_path = Path(".env")

    if not env_path.exists():
        print(f"⚠️  .env file not found. Copy from .env.example: cp .env.example .env")
        return False

    with open(".env") as f:
        content = f.read()

    required_keys = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "TAVILY_API_KEY",
    ]

    all_ok = True
    for key in required_keys:
        if f"{key}=" in content:
            # Check if value is set (not just placeholder)
            val = [line.split("=", 1)[1].strip() for line in content.split("\n") if line.startswith(f"{key}=")]
            if val and val[0] and not val[0].endswith("..."):
                print(f"✅ {key} configured")
            else:
                print(f"⚠️  {key} = placeholder. Set actual value in .env")
                all_ok = False
        else:
            print(f"❌ {key} missing from .env")
            all_ok = False

    return all_ok


def check_project_structure():
    """Verify expected directories exist"""
    dirs = [
        "agents", "tools", "models", "config", "guardrails", "hooks", "db", "chroma", "app", "tests", "data", "logs"
    ]

    all_ok = True
    for d in dirs:
        if Path(d).exists():
            print(f"✅ {d}/")
        else:
            print(f"❌ {d}/ missing")
            all_ok = False

    return all_ok


def check_api_connectivity():
    """Test API connectivity (optional, requires valid keys)"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  dotenv not available, skipping .env load")
        return True

    print("\n--- API Connectivity Check ---")

    # Test Anthropic
    try:
        import anthropic
        key = os.environ.get("ANTHROPIC_API_KEY")
        if key and not key.endswith("..."):
            client = anthropic.Anthropic(api_key=key)
            _ = client.messages.create(
                model="claude-opus-4-1",
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}]
            )
            print("✅ Anthropic API: reachable")
        else:
            print("⚠️  Anthropic API: key not configured")
    except Exception as e:
        print(f"❌ Anthropic API: {type(e).__name__}: {str(e)[:60]}")

    # Test OpenAI
    try:
        from openai import OpenAI
        key = os.environ.get("OPENAI_API_KEY")
        if key and not key.endswith("..."):
            client = OpenAI(api_key=key)
            _ = client.models.list()
            print("✅ OpenAI API: reachable")
        else:
            print("⚠️  OpenAI API: key not configured")
    except Exception as e:
        print(f"❌ OpenAI API: {type(e).__name__}: {str(e)[:60]}")

    # Test Tavily
    try:
        from tavily import TavilyClient
        key = os.environ.get("TAVILY_API_KEY")
        if key and not key.endswith("..."):
            client = TavilyClient(api_key=key)
            print("✅ Tavily API: client initialized")
        else:
            print("⚠️  Tavily API: key not configured")
    except Exception as e:
        print(f"⚠️  Tavily API: {type(e).__name__}")

    return True


def main():
    print("=" * 60)
    print("PHASE 0 — ENVIRONMENT VALIDATION")
    print("=" * 60)
    print()

    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_venv),
        ("Dependencies", check_dependencies),
        ("Project Structure", check_project_structure),
        ("Environment File", check_env_file),
    ]

    results = []
    for name, check_fn in checks:
        print(f"\n--- {name} ---")
        try:
            result = check_fn()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Check failed: {e}")
            results.append((name, False))

    # Optional API check
    check_api_connectivity()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n✅ Phase 0 validation PASSED. Ready to proceed to Phase 1.")
        return 0
    else:
        print("\n⚠️  Some checks failed. Review and resolve above issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
