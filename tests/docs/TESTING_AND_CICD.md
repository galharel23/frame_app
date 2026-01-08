# CI/CD Pipeline & Testing Guide

## Overview

This document outlines the testing strategy and CI/CD pipeline for the WhiteBox application.

---

## 🧪 Unit Testing

### Setup

Testing dependencies have been installed:
```bash
pip install pytest pytest-cov pytest-asyncio pytest-mock
```

### Running Tests

Run all tests:
```bash
pytest
```

Run specific test file:
```bash
pytest tests/test_srt_service.py -v
```

Run with coverage report:
```bash
pytest --cov=. --cov-report=html
```

View HTML coverage report:
```
Open coverage_report/index.html in your browser
```

### Test Structure

Tests are organized by module:
- `tests/test_srt_service.py` - SRT processing and CSV export
- `tests/test_utils_service.py` - Utility helper functions
- `tests/test_design_system.py` - Design system constants and colors

### Test Markers

Tests can be marked with categories:
```bash
pytest -m unit          # Run only unit tests
pytest -m integration   # Run integration tests
pytest -m slow          # Run slow tests
```

---

## 🚀 CI/CD Pipeline

### GitHub Actions Workflow

The CI/CD pipeline is defined in `.github/workflows/tests.yml`

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`
- Daily scheduled run (2 AM UTC)

### Pipeline Stages

#### 1. **Test Stage** (Runs on Windows)
   - Python 3.10, 3.11, 3.12 (matrix testing)
   - Installs dependencies
   - Runs pytest with coverage
   - Uploads coverage to CodeCov

   **Status Checks:**
   - ✅ All tests must pass
   - ✅ Code coverage should be > 80%

#### 2. **Code Quality Stage**
   - **Black**: Code formatting check
   - **isort**: Import sorting verification
   - **Flake8**: Linting and code style
   - **Pylint**: Advanced code analysis

   **Configuration:**
   - Max line length: 127 characters
   - Max complexity: 10 (cyclomatic)

#### 3. **Build Stage**
   - Only runs if tests & quality checks pass
   - Uses PyInstaller to build Windows executable
   - Uploads build artifact for download

### Coverage Requirements

- **Minimum Coverage**: 80%
- **Critical Modules**: 90%+
- Coverage report: `coverage.xml` & `coverage_report/`

---

## 📋 Testing Best Practices

### Writing Tests

1. **Test Organization**
   ```python
   class TestModuleName:
       def test_specific_functionality(self):
           # Arrange
           input_data = ...

           # Act
           result = function(input_data)

           # Assert
           assert result == expected
   ```

2. **Use Fixtures** (in `conftest.py`)
   ```python
   @pytest.fixture
   def sample_metadata():
       return VideoFrameMetadata(...)
   ```

3. **Parametrized Tests**
   ```python
   @pytest.mark.parametrize("input,expected", [
       (1, 2),
       (2, 4),
       (3, 6),
   ])
   def test_double(input, expected):
       assert double(input) == expected
   ```

4. **Async Tests** (with `pytest-asyncio`)
   ```python
   @pytest.mark.asyncio
   async def test_async_function():
       result = await async_function()
       assert result == expected
   ```

### Test Coverage Goals

- Services: 85%+ coverage
- Utils: 90%+ coverage
- Screens: 50%+ (UI testing is harder)

---

## 📊 Local Development Workflow

### Before Committing

```bash
# 1. Run tests locally
pytest

# 2. Check code formatting
black . --check

# 3. Sort imports
isort . --check-only

# 4. Lint code
flake8 .

# 5. Run with coverage
pytest --cov=. --cov-report=term-missing
```

### Format Code Automatically

```bash
# Format all code
black .

# Sort imports
isort .
```

---

## 🔄 Future Enhancements

### Recommended Additions

1. **Integration Tests**
   - Test full workflows (image → metadata → CSV)
   - Test file I/O operations
   - Test error handling

2. **Performance Testing**
   - Benchmark large batch processing
   - Memory profiling
   - UI responsiveness testing

3. **Security Scanning**
   - SAST (Static Application Security Testing)
   - Dependency vulnerability scanning (using `safety`)
   - Code scanning with GitHub's native tools

4. **Docker Support**
   ```dockerfile
   FROM python:3.12-slim
   WORKDIR /app
   COPY . .
   RUN pip install -r requirements.txt
   CMD ["python", "app.py"]
   ```

5. **Automated Releases**
   - Tag-based releases
   - Automated version bumping
   - Asset uploads to GitHub Releases

6. **Pre-commit Hooks**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

---

## 📈 Monitoring & Analytics

### CodeCov Integration

- Coverage reports uploaded automatically
- Pull requests show coverage changes
- Badges can be added to README

### GitHub Issues Integration

- Failing tests create issues automatically
- Link PRs to issues
- Auto-close on merge

---

## 🛠️ Troubleshooting

### Tests failing locally but passing in CI?
- Check Python version (`python --version`)
- Verify dependencies: `pip install -r requirements.txt`
- Clear cache: `pytest --cache-clear`

### Coverage not matching?
- Some paths may only execute in specific OS
- UI code is harder to test
- Use `# pragma: no cover` for untestable code

### Build artifacts not generated?
- Check PyInstaller errors: `pyinstaller app.spec --debug all`
- Verify all imports are resolvable
- Check for missing DLLs or resources

---

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [GitHub Actions](https://github.com/features/actions)
- [Black Code Formatter](https://black.readthedocs.io/)
- [PyInstaller](https://pyinstaller.org/)

---

## 📝 Checklist for New Features

- [ ] Write unit tests (aim for 80%+ coverage)
- [ ] Run `pytest` locally - all tests pass
- [ ] Run `black .` to format code
- [ ] Run `isort .` to sort imports
- [ ] Run `flake8 .` for linting
- [ ] Commit and push to trigger CI/CD
- [ ] Verify GitHub Actions workflow passes
- [ ] Merge to main/develop after approval

---

**Last Updated**: January 8, 2026
**Version**: 1.0
