# Contributing to AI Frappe App Builder

We welcome contributions to the AI Frappe App Builder!

## 1. Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/ai-frappe-builder.git
cd ai-frappe-builder

# Install dependencies (Python 3.11+)
make install

# Install frontend dependencies
cd frontend && npm install && cd ..
```

## 2. Operating Principles
- **No Stubs, No Partial TODOs**: Implement and test every function.
- **Strict Typing**: Code must pass `mypy --strict` and `tsc --noEmit`.
- **Ruff Clean**: Python code must pass `ruff check .` and `ruff format --check .`.
- **Tests Always Green**: Run `make test` before submitting changes.
- **Conventional Commits**: Format commit messages as `feat:`, `fix:`, `test:`, `docs:`, `refactor:`.

## 3. Pull Request Checklist
1. All unit, contract, and golden tests pass (`make test`).
2. Type checking is 100% clean (`make typecheck`).
3. Linter is 100% clean (`make lint`).
4. Frontend builds cleanly (`cd frontend && npm run build`).
