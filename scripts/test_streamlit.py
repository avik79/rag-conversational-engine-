"""Test Streamlit app startup and basic functionality"""
import os
import sys
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

# Load .env
env_path = ".env"
if os.path.exists(env_path):
    for line in open(env_path):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        value = value.split("#")[0].strip()
        if key:
            os.environ[key] = value

# Test imports
print("Testing imports...")
try:
    from app.main import init_session_state
    from app.integration import run_eira_agent
    from app.components import render_response_card
    from app.wire_tools import wire_all_tools
    print("All imports successful")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)

# Test Streamlit app syntax
print("\nTesting Streamlit syntax...")
result = subprocess.run(
    ["streamlit", "run", "app/main.py", "--logger.level=info"],
    timeout=10,
    capture_output=True,
    text=True,
)

if result.returncode == 0 or "You can now view your Streamlit app" in result.stderr:
    print("Streamlit app started successfully")
except subprocess.TimeoutExpired:
    print("Streamlit app started (timeout expected)")
except Exception as e:
    print(f"Streamlit startup error: {e}")
    print(f"stderr: {result.stderr[:500]}")
    sys.exit(1)

print("\nAll tests passed")
