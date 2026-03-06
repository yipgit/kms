# VS Code Testing Setup - Quick Reference

## ✅ Configuration Complete!

I've set up the following files for you:
- [`pytest.ini`](file:///d:/code/kms/pytest.ini) - Pytest configuration
- [`.vscode/settings.json`](file:///d:/code/kms/.vscode/settings.json) - VS Code testing settings
- [`.vscode/extensions.json`](file:///d:/code/kms/.vscode/extensions.json) - Recommended extensions

---

## 🚀 How to Use Testing in VS Code

### Step 1: Install Recommended Extensions
VS Code should prompt you to install recommended extensions. Click **Install All** or install manually:
- **Python** (ms-python.python)
- **Pylance** (ms-python.vscode-pylance)
- **Coverage Gutters** (ryanluker.vscode-coverage-gutters) - Optional, for visual coverage

### Step 2: Activate Your Virtual Environment
Make sure your Python interpreter is set to the venv:
1. Press `Ctrl+Shift+P`
2. Type "Python: Select Interpreter"
3. Choose `.\venv\Scripts\python.exe`

### Step 3: Open Testing Panel
- Click the **Testing** icon in the Activity Bar (flask/beaker icon on the left)
- Or press `Ctrl+Shift+T`
- VS Code will automatically discover your tests

### Step 4: Run Tests
You have several options:

**Option A: Testing Panel**
- Click the ▶️ play button next to any test to run it
- Click the ▶️ at the top to run all tests
- Right-click for more options (Debug, Run with Coverage, etc.)

**Option B: Code Lens (in the editor)**
- Look for "Run Test" | "Debug Test" links above each test function
- Click to run individual tests

**Option C: Command Palette**
- `Ctrl+Shift+P` → "Test: Run All Tests"
- `Ctrl+Shift+P` → "Test: Run Test at Cursor"

**Option D: Terminal**
```bash
# Activate venv first
.\venv\Scripts\activate

# Run all tests
pytest

# Run specific file
pytest tests/test_telegram_bot.py

# Run with coverage
pytest --cov=src --cov-report=html
```

---

## 🎯 Test Features Configured

### Async Test Support
Your tests use `unittest.IsolatedAsyncioTestCase`, which pytest handles automatically with the `asyncio_mode = auto` setting.

### Code Coverage
- Terminal coverage report shows after each test run
- HTML report generated in `htmlcov/` folder
- Open `htmlcov/index.html` in browser to see detailed coverage

### Test Discovery
- Automatically finds all `test_*.py` files in `tests/` folder
- Discovers all `test_*` functions and `Test*` classes

---

## 🐛 Debugging Tests

1. Set breakpoints in your test code (click left of line number)
2. Right-click the test in Testing panel → **Debug Test**
3. Or click "Debug Test" code lens above the test function
4. Use the Debug toolbar to step through code

---

## 💡 Tips

- **Auto-run on save**: Tests auto-discover when you save files
- **Filter tests**: Use the filter box in Testing panel to search
- **View output**: Click on a test result to see detailed output
- **Coverage visualization**: Install Coverage Gutters extension, then run tests with coverage and click "Watch" in the status bar

---

## 🔧 Troubleshooting

**Tests not appearing?**
1. Make sure Python extension is installed
2. Check that interpreter is set to `.\venv\Scripts\python.exe`
3. Reload window: `Ctrl+Shift+P` → "Developer: Reload Window"

**Import errors?**
- The `python.analysis.extraPaths` setting should help VS Code find your `src` module
- Make sure you're running tests from the project root

**Async tests failing?**
- The `asyncio_mode = auto` in `pytest.ini` should handle this
- Make sure `pytest-asyncio` is installed (it's in your requirements.txt)

---

## 📚 Current Test File

Your [`test_telegram_bot.py`](file:///d:/code/kms/tests/test_telegram_bot.py) contains:
- ✅ 3 async test cases
- ✅ Proper mocking with `AsyncMock` and `MagicMock`
- ✅ Tests for authorized/unauthorized access
- ✅ Callback handler testing

Ready to run! 🎉
