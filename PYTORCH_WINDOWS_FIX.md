# PyTorch Windows DLL Fix

## Issue

```
OSError: [WinError 1114] A dynamic link library (DLL) initialization routine failed.
Error loading "c10.dll" or one of its dependencies.
```

This occurs when PyTorch is incompatible with your Python version or Windows environment.

## Solution

### Fix for Windows Python 3.14+

The issue is that PyTorch 2.12.0 doesn't have wheels built for Python 3.14.

**Apply this fix:**

```bash
# 1. Upgrade torch with CPU-only support
python -m pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 2. Upgrade transformers and sentence-transformers
python -m pip install --upgrade transformers sentence-transformers

# 3. Clear cache
python -m pip cache purge

# 4. Verify installation
python -c "import torch; print(torch.__version__)"

# 5. Restart streamlit
streamlit run app/main.py
```

### If Issue Persists

Try downgrading to Python 3.11:

```bash
# Check Python version
python --version

# If 3.14, consider using 3.11 instead
# Most packages have better support for 3.11

# To create new venv with Python 3.11:
# 1. Install Python 3.11 from python.org
# 2. Create venv: python3.11 -m venv .venv311
# 3. Activate and install: uv sync
```

### Alternative: CUDA Version (if you have NVIDIA GPU)

```bash
# For GPU support
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## What Was Changed

- PyTorch: 2.12.0 → 2.12.1+cpu
- Transformers: 5.12.0 → 5.12.1
- Sentence-Transformers: 5.5.1 → 5.6.0

## Verification

```bash
# Check installation
python -c "
import torch
import transformers
from sentence_transformers import SentenceTransformer

print(f'PyTorch: {torch.__version__}')
print(f'Transformers: {transformers.__version__}')
print('All imports successful!')
"

# Run streamlit
streamlit run app/main.py
```

## Prevention

Update `pyproject.toml` to use flexible version constraints:

```toml
torch = ">=2.12,<3.0"
transformers = ">=5.10,<6.0"
sentence-transformers = ">=5.5,<6.0"
```

## FAQ

**Q: Why did this happen?**
A: Python 3.14 is very new and not all packages have optimized wheels for it yet.

**Q: Will it happen again?**
A: When updating dependencies, run: `uv sync` which resolves compatible versions.

**Q: Is there a performance impact?**
A: No, CPU version performs identically to GPU version if you don't have CUDA.

**Q: Should I use Python 3.11 instead?**
A: If this occurs again, yes. Python 3.11 has mature package support and is production-standard.

## Support

If the issue persists:
1. Check Python version: `python --version`
2. Try Python 3.11: `py -3.11 --version`
3. Create fresh venv with 3.11
4. Report issue with full error message

---

**Fixed:** 2026-06-19
**Versions Updated:** torch, transformers, sentence-transformers
**Status:** ✅ Resolved
