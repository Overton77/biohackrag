# Python Import Troubleshooting Guide: Fixing "No module named 'src'" Errors

## Overview

This guide explains how to fix the common `ModuleNotFoundError: No module named 'src'` error that occurs when working with Python projects that have a nested directory structure. This error typically happens when you're trying to import modules from within a `src/` directory while running code from different locations.

## The Problem

### What Happens

When you get this error:

```python
ModuleNotFoundError: No module named 'src'
```

It means Python cannot find the `src` module in its search path. This commonly occurs when:

1. **Running from nested directories**: You're executing code from `backend/src/ingestion/indexing/` but trying to import `from src.config.mongo_setup`
2. **Incorrect path setup**: The Python path doesn't include the right directories
3. **Mixed import styles**: Some files use absolute imports (`from src.config.mongo_setup`) while others use relative imports

### Why It Happens

Python's import system works by searching for modules in directories listed in `sys.path`. When you're in `backend/src/ingestion/indexing/`:

- **Current working directory**: `backend/src/ingestion/indexing/`
- **Python path**: Only includes current directory and system paths
- **Missing**: The `backend/` directory that contains `src/` as a subdirectory

## The Solution

### Method 1: Fix Import Statements (Recommended)

**Problem**: Files inside `src/` were using absolute imports with `src.` prefix:

```python
# ❌ This won't work from inside src/
from src.config.mongo_setup import get_async_mongo_client
```

**Solution**: Change to relative imports:

```python
# ✅ This works from inside src/
from config.mongo_setup import get_async_mongo_client
```

### Method 2: Fix Python Path in Notebooks

**Problem**: Notebook was adding incorrect path:

```python
# ❌ This only goes up to backend/src/
sys.path.append(os.path.join(os.getcwd(), '..', '..'))
```

**Solution**: Add the correct path to make `src` importable:

```python
# ✅ Option A: Add backend directory to path (allows 'src.' imports)
sys.path.append(os.path.join(os.getcwd(), '..', '..', '..'))
# Now you can use: from src.mongo_schema_overwrite import *

# ✅ Option B: Add src directory directly to path (allows direct imports)
sys.path.append(os.path.join(os.getcwd(), '..', '..'))
# Now you can use: from mongo_schema_overwrite import *
```

## Directory Structure Understanding

```
BioHackAgent/
├── backend/                    # ← This is the project root
│   ├── src/                   # ← This is the src module
│   │   ├── config/
│   │   │   └── mongo_setup.py
│   │   ├── ingestion/
│   │   │   └── indexing/
│   │   │       └── lg_transcript_tests.ipynb  # ← You're here
│   │   └── mongo_schema_overwrite.py
│   └── webpage_parsing/       # ← This is at same level as src
│       └── mongo_recent_data.py
```

### Path Navigation from `lg_transcript_tests.ipynb`:

- **Current location**: `backend/src/ingestion/indexing/`
- **To reach `src/`**: `'..', '..'` (go up 2 levels)
- **To reach `backend/`**: `'..', '..', '..'` (go up 3 levels)

## Import Strategies

### 1. Relative Imports (Inside `src/`)

Files inside the `src/` directory should use relative imports:

```python
# ✅ Good - relative imports from inside src/
from config.mongo_setup import get_async_mongo_client
from mongo_schemas import init_beanie_with_pymongo
from ingestion.indexing.tools.transcript_ingestion_tools import submit_product_information
```

### 2. Absolute Imports (Outside `src/`)

Files outside the `src/` directory can use absolute imports with `src.` prefix:

```python
# ✅ Good - absolute imports from outside src/
from src.config.mongo_setup import get_async_mongo_client
from src.mongo_schema_overwrite import init_beanie_with_pymongo
```

### 3. Mixed Strategy (Not Recommended)

Avoid mixing import styles within the same directory:

```python
# ❌ Bad - mixing import styles
from config.mongo_setup import get_async_mongo_client  # relative
from src.mongo_schemas import init_beanie_with_pymongo  # absolute
```

## Step-by-Step Fix

### Step 1: Fix Import Statements in `src/` Files

Update all files inside `src/` to use relative imports:

```python
# Before (❌)
from src.config.mongo_setup import get_async_mongo_client

# After (✅)
from config.mongo_setup import get_async_mongo_client
```

### Step 2: Fix Notebook Path Setup

In your notebook, choose one approach:

**Option A - Add backend to path:**

```python
import sys
import os
# Add the backend directory to the Python path so we can import from src
sys.path.append(os.path.join(os.getcwd(), '..', '..', '..'))
# Now you can import like this:
from src.mongo_schema_overwrite import *
```

**Option B - Add src to path:**

```python
import sys
import os
# Add the src directory to the Python path
sys.path.append(os.path.join(os.getcwd(), '..', '..'))
# Now you can import like this:
from mongo_schema_overwrite import *
```

### Step 3: Test Your Fix

Create a simple test script to verify imports work:

```python
#!/usr/bin/env python3
"""
Test script to verify that imports are working correctly.
Run this from the backend directory.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from mongo_schema_overwrite import Person, Episode, Transcript
    print("✅ Successfully imported from mongo_schema_overwrite")

    from config.mongo_setup import get_async_mongo_client
    print("✅ Successfully imported from config.mongo_setup")

    print("\n🎉 All imports working correctly!")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
```

## Best Practices

### 1. Consistent Import Style

- **Inside `src/`**: Use relative imports
- **Outside `src/`**: Use absolute imports with `src.` prefix
- **Never mix**: Don't use both styles in the same file

### 2. Path Management

- **For notebooks**: Add the appropriate directory to `sys.path`
- **For scripts**: Use relative imports or run from the correct directory
- **For modules**: Use `uv run python -m module_name.file_name`

### 3. Project Structure

```
backend/
├── src/                       # Python package
│   ├── __init__.py           # Makes src a package
│   ├── config/
│   │   ├── __init__.py       # Makes config a package
│   │   └── mongo_setup.py
│   └── ingestion/
│       ├── __init__.py       # Makes ingestion a package
│       └── indexing/
│           └── lg_transcript_tests.ipynb
└── webpage_parsing/           # Separate module
    └── mongo_recent_data.py
```

## Common Mistakes to Avoid

### 1. Wrong Path Calculation

```python
# ❌ Wrong - only goes up to src/
sys.path.append(os.path.join(os.getcwd(), '..', '..'))

# ✅ Correct - goes up to backend/
sys.path.append(os.path.join(os.getcwd(), '..', '..', '..'))
```

### 2. Inconsistent Import Styles

```python
# ❌ Don't mix styles
from config.mongo_setup import get_async_mongo_client      # relative
from src.mongo_schemas import init_beanie_with_pymongo     # absolute
```

### 3. Running from Wrong Directory

```bash
# ❌ Wrong - running from inside src/
cd backend/src/ingestion/indexing
python lg_transcript_tests.ipynb

# ✅ Correct - running from backend/
cd backend
uv run python -m src.ingestion.indexing.lg_transcript_tests
```

## Troubleshooting Checklist

- [ ] Are all files inside `src/` using relative imports?
- [ ] Are all files outside `src/` using absolute imports with `src.` prefix?
- [ ] Is the Python path correctly set in your notebook?
- [ ] Are you running from the correct directory?
- [ ] Do all directories have `__init__.py` files?

## Summary

The key to fixing `ModuleNotFoundError: No module named 'src'` is:

1. **Use relative imports inside `src/`**: `from config.mongo_setup import ...`
2. **Use absolute imports outside `src/`**: `from src.config.mongo_setup import ...`
3. **Set correct Python path in notebooks**: Add either `backend/` or `src/` to `sys.path`
4. **Maintain consistent import style**: Don't mix relative and absolute imports

By following these principles, you'll have a clean, maintainable import structure that works regardless of where you run your code from.
