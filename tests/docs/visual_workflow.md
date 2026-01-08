┌─────────────────────────────────┐
│ Edit your code files            │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ git add .                       │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ git commit -m "message"         │
└──────────────┬──────────────────┘
               │
               ▼ Pre-commit hooks run (local)
        ┌──────────────┐
        │ ✅ Black     │
        │ ✅ isort     │
        │ ✅ Flake8    │
        │ ✅ File chks │
        └──────────────┘
               │
        ┌──────┴──────┐
        │             │
    ❌ FAIL        ✅ PASS
        │             │
    Fix issues     Commit OK
        │             │
    Retry ◄──────────┘
               │
               ▼
┌─────────────────────────────────┐
│ git push origin main            │
└──────────────┬──────────────────┘
               │
               ▼ GitHub Actions runs (remote)
        ┌──────────────────────┐
        │ ✅ pytest (106 tests)│
        │ ✅ Code quality      │
        │ ✅ Build executable  │
        └──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
    ❌ FAIL        ✅ PASS
     (show X)    (show ✓)
