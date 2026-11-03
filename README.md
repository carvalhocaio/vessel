# python-template

A minimalist, modern Python project template preconfigured with:
- **Python 3.12+** and packaging via PEP 621 (`pyproject.toml` + `hatchling`)
- **[uv](https://github.com/astral-sh/uv)** for fast package and virtual environment management
- **[Ruff](https://github.com/astral-sh/ruff)** for linting and formatting (PEP 8 compliant, 88 columns)
- **[Pyright](https://github.com/microsoft/pyright)** for static type checking
- **[Pre-commit](https://pre-commit.com/)** git hooks for code hygiene and security
- **[Pytest](https://pytest.org/)** test runner with smoke test
- **[pip-audit](https://github.com/pypa/pip-audit)** for dependency vulnerability scanning
- **Idiomatic Makefile** for development workflow automation
- **GitHub Actions CI** matching local checks

---

## Quickstart

### 1. Using this template

Click **"Use this template"** on GitHub or clone the repository:

```bash
git clone https://github.com/<username>/<repo-name>.git
cd <repo-name>
```

### 2. Rename the project

Run the renaming helper to configure your package name and update `pyproject.toml` and tests:

```bash
make rename NAME=my-new-project
```

### 3. Install dependencies and git hooks

```bash
make sync
make hooks
```

---

## Available Commands

| Command | Description |
|---|---|
| `make help` | Show all available commands |
| `make sync` | Install runtime and dev dependencies using `uv` |
| `make hooks` | Install pre-commit hooks into `.git/hooks` |
| `make hooks-run` | Run pre-commit checks on all files |
| `make test` | Run tests with `pytest` |
| `make lint` | Check code with `ruff` |
| `make lint-fix` | Automatically fix linting issues |
| `make format` | Format code with `ruff` |
| `make format-check` | Check code formatting without modifying |
| `make typecheck` | Run static type checking with `pyright` |
| `make audit` | Audit dependencies for vulnerabilities with `pip-audit` |
| `make ci` | Run full verification pipeline locally (`lint`, `format-check`, `typecheck`, `audit`, `test`) |
| `make clean` | Remove caches and build artifacts |
| `make rename NAME=...` | Rename package and update configuration |

---

## Project Structure

```text
.
├── .github/workflows/ci.yml   # GitHub Actions CI workflow
├── src/
│   └── app_name/              # Source code directory (renamed via make rename)
│       ├── __init__.py
│       └── py.typed
├── tests/
│   ├── __init__.py
│   └── test_smoke.py          # Initial smoke test
├── .gitignore
├── .pre-commit-config.yaml
├── .python-version
├── Makefile
├── pyproject.toml
└── README.md
```
