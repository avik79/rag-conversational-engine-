# Install Python 3.11 & Fix PyTorch Issue

## Problem
You have Python 3.14, but PyTorch 2.12+ doesn't support it yet. Solution: **Use Python 3.11**

## Quick Fix (5 minutes)

### Step 1: Install Python 3.11
Go to: https://www.python.org/downloads/release/python-3119/

**Download:** Windows installer (64-bit) - `python-3.11.9-amd64.exe`

**During installation:**
- ✅ Check "Add python.exe to PATH"
- ✅ Check "Install for all users" (optional)
- ✅ Click "Install Now"

### Step 2: Verify Installation
```bash
py -3.11 --version
# Should show: Python 3.11.9
```

### Step 3: Delete Old Environment
```bash
cd C:\Users\vmuser\Documents\rag-conversational-engine
rmdir /s /q .venv
```

### Step 4: Create New Environment with Python 3.11
```bash
py -3.11 -m venv .venv
```

### Step 5: Activate & Install
```bash
# Activate
.venv\Scripts\activate

# Verify Python 3.11
python --version
# Should show: Python 3.11.9

# Install dependencies
pip install --upgrade pip
pip install -e .
uv sync

# Verify PyTorch works
python -c "import torch; print(f'✓ PyTorch {torch.__version__}')"
```

### Step 6: Run App
```bash
streamlit run app/main.py
```

---

## If You Don't Have Python 3.11

### Option A: Install from python.org (Recommended)
1. Go to https://www.python.org/downloads/
2. Click "Downloads" → "Windows"
3. Download "Python 3.11.9" Windows installer
4. Run installer, check "Add to PATH"
5. Follow Step 2 onwards above

### Option B: Install via Windows Package Manager
```bash
winget install Python.Python.3.11
```

### Option C: Install via Chocolatey
```bash
choco install python311
```

---

## Troubleshooting

### "py -3.11 not found"
**Solution:** Reinstall Python 3.11, ensure "Add to PATH" is checked

### "Permission denied" deleting .venv
**Solution:** Restart PowerShell/CMD and try again

### "System cannot find the path specified"
**Solution:** Make sure you're in the correct directory:
```bash
cd C:\Users\vmuser\Documents\rag-conversational-engine
```

### PyTorch still fails after install
**Solution:** Delete venv again and reinstall:
```bash
rmdir /s /q .venv
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

---

## Verify Success

```bash
# Check Python version
python --version
# Output: Python 3.11.9

# Check torch
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
# Output: PyTorch: 2.12.1+cpu

# Check transformers
python -c "import transformers; print(f'Transformers: {transformers.__version__}')"
# Output: Transformers: 5.12.1

# Run app
streamlit run app/main.py
# App should open on http://localhost:8501
```

---

## Why Python 3.11?

| Feature | Python 3.11 | Python 3.14 |
|---------|------------|-----------|
| PyTorch 2.12+ | ✅ Full support | ❌ No support |
| Production ready | ✅ Stable (LTS) | ⚠️ Experimental |
| Package support | ✅ Complete | ⚠️ Partial |
| Security | ✅ Active | ✅ Latest |
| Performance | ✅ Good | ✅ Better (but no PyTorch) |

---

## Time To Fix

- Download Python: 2 min
- Install Python: 2 min
- Create venv: 1 min
- Install deps: 3 min
- **Total: ~8 minutes**

---

## Next Steps

Once Python 3.11 is set up:
1. Test app locally: `streamlit run app/main.py`
2. Try HITL: Query with low confidence
3. Check CI/CD: `.github/workflows/`
4. Deploy: `docker-compose up`

---

**Created:** 2026-06-19
**For:** Python 3.14 PyTorch compatibility issue
**Solution:** Use Python 3.11 (LTS, production-standard)
**Status:** This resolves the DLL error permanently ✅
