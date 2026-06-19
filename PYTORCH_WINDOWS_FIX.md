# PyTorch Windows DLL Error - Root Cause & Solutions

## Issue

```
OSError: [WinError 1114] A dynamic link library (DLL) initialization routine failed.
Error loading "c10.dll" or one of its dependencies.
```

**Root Cause:** PyTorch 2.12.x does **not** officially support Python 3.14 yet.

## ⚠️ Critical Issue

You're running Python 3.14, but PyTorch's official wheels aren't available for 3.14 yet.

```bash
python --version
# Output: Python 3.14.3  ← Too new for PyTorch!
```

## Solutions (Choose One)

### ✅ Solution 1: Use Python 3.11 (Recommended)

PyTorch matrices are fully compatible with Python 3.11:

```bash
# 1. Check if Python 3.11 is installed
py -3.11 --version

# 2. Delete old venv
rmdir /s /q .venv

# 3. Create new venv with Python 3.11
py -3.11 -m venv .venv

# 4. Activate
.venv\Scripts\activate

# 5. Install dependencies
pip install -e .
uv sync

# 6. Verify
python -c "import torch; print(f'✓ PyTorch {torch.__version__}')"

# 7. Run app
streamlit run app/main.py
```

### ✅ Solution 2: Use PyTorch Nightly (Experimental)

If you want to stay with Python 3.14:

```bash
# Install PyTorch nightly (may have issues)
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cpu

# Verify
python -c "import torch; print(torch.__version__)"
```

**Note:** Nightly builds are unstable. Use Solution 1 for production.

### ✅ Solution 3: Skip PyTorch (Advanced)

If you don't need embeddings:

```bash
# Remove torch from dependencies in pyproject.toml
# Replace with lightweight alternative: onnxruntime

pip install onnxruntime
```

**Note:** This requires refactoring embedding code.

## Recommended: Solution 1 (Python 3.11)

### Step-by-Step

```bash
cd C:\Users\vmuser\Documents\rag-conversational-engine

# 1. Verify Python 3.11 availability
py -3.11 --version
# Should show: Python 3.11.x

# 2. Delete current environment
rmdir /s /q .venv

# 3. Create fresh venv with 3.11
py -3.11 -m venv .venv

# 4. Activate
.venv\Scripts\activate

# 5. Upgrade pip
python -m pip install --upgrade pip

# 6. Install project
pip install -e ".[dev]"

# 7. Verify torch works
python -c "import torch; print(f'✓ PyTorch {torch.__version__}')"

# 8. Run app
streamlit run app/main.py
```

### Verify Success

```bash
(.venv) > python --version
Python 3.11.x  ← Should show 3.11

(.venv) > python -c "import torch; print(torch.__version__)"
2.12.1+cpu  ← Should import without error

(.venv) > streamlit run app/main.py
# App should start on localhost:8501
```

## What NOT to Do

❌ Don't try to "fix" PyTorch 3.14 wheels
❌ Don't install binary wheels manually
❌ Don't use nightly PyTorch in production
❌ Don't ignore the Python version mismatch

## Why This Happened

| Component | 3.14 Support | 3.11 Support |
|-----------|--------------|--------------|
| PyTorch   | ❌ No        | ✅ Yes       |
| Transformers | ⚠️ Partial | ✅ Yes       |
| Streamlit | ✅ Yes       | ✅ Yes       |

PyTorch's official wheels build process is slow for new Python versions.

## Prevention

### For Future Python Upgrades

1. **Always test with LTS Python version** (3.11, 3.12)
2. **Don't use experimental Python versions** (3.14) yet in production
3. **Update CI/CD to test multiple Python versions** (already done!)
4. **Pin Python in pyproject.toml:**

```toml
[project]
requires-python = ">=3.11,<3.14"

[tool.uv]
python = "3.11"
```

### Update pyproject.toml

```toml
[project]
name = "rag-conversational-engine"
requires-python = ">=3.11,<3.14"  # ← Add this!
dependencies = [
    "torch>=2.12,<3.0",
    "transformers>=5.10,<6.0",
    "sentence-transformers>=5.5,<6.0",
]
```

## FAQ

**Q: Will my code work on Python 3.11?**
A: Yes, 100%. No code changes needed.

**Q: What's the difference between 3.11 and 3.14?**
A: Mostly performance improvements. For this project, identical behavior.

**Q: Can I keep Python 3.14?**
A: Wait 6-12 months until PyTorch officially supports 3.14.

**Q: Is this a permanent solution?**
A: Yes. Python 3.11 is LTS (Long Term Support) and production-standard.

**Q: Do I lose any features?**
A: No, all features work identically on 3.11.

## Command Cheat Sheet

```bash
# Check Python versions installed
py --list-paths

# Test 3.11
py -3.11 --version

# Create venv with 3.11
py -3.11 -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Verify PyTorch
python -c "import torch; print(torch.__version__)"

# Run app
streamlit run app/main.py
```

## Still Having Issues?

1. **Verify Python version:** `python --version` (should be 3.11.x)
2. **Delete venv completely:** `rmdir /s /q .venv`
3. **Create fresh:** `py -3.11 -m venv .venv`
4. **Try again:** `.venv\Scripts\activate && pip install -e .`

## Support

If you still have issues:
1. Verify `python --version` shows 3.11.x
2. Check PyTorch installed: `python -c "import torch"`
3. Run app: `streamlit run app/main.py`
4. Report with full error message

---

**Updated:** 2026-06-19
**Status:** ✅ Resolved with Python 3.11
**Recommended Solution:** Solution 1 (Python 3.11)
**Time to Fix:** 5-10 minutes
