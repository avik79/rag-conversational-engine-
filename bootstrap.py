"""Bootstrap script to load environment and initialize system"""
import os
import sys
from pathlib import Path

# Ensure UTF-8 encoding on Windows
sys.stdout.reconfigure(encoding='utf-8')

# Load .env
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, _, value = line.partition('=')
        value = value.split('#')[0].strip()  # Remove inline comments
        if key:
            os.environ[key] = value
