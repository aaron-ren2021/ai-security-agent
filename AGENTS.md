# Repository Guidelines

## Setup & Initialization
- `git clone <repo-url> && cd ai-security-agent` pulls the codebase targeted by this guide.
- `uv sync` (or `pip install -r requirements.txt`) installs runtime and dev dependencies for Python 3.11.
- Populate `.env` with Azure AI Projects, Search, OpenAI, and OAuth secrets (see README 快速開始) before running the app.
- Seed the SQLite auth database once with `python -c "from src.models.auth import init_db; init_db()"`.

## Project Structure & Module Organization
- `src/` houses the Flask app; `main.py` boots the server, `core/` holds shared logic, `routers/` and `routes/` expose HTTP endpoints, and `services/` wraps Azure AI workflows.
- `models/` contains SQLAlchemy entities and Pydantic schemas; UI assets live in `frontend/` and `static/`, reusable templates in `template/`, and binary assets in `assets/`.
- `tests/` mirrors runtime modules with unit, integration, and slow Azure coverage; fixtures and sample payloads sit in `test_files/`, while longer docs belong in `docs/`.

## Build, Test, and Development Commands
- `python src/main.py` launches the development server with auto-reload via `watchfiles`.
- `pytest` runs the full suite; append `-m "not slow"` to skip Azure live calls or target a marker, e.g. `pytest -m fastapi tests/test_ai_functionality.py`.
- `pytest --cov=src` produces coverage summaries when PRs need evidence.

## Coding Style & Naming Conventions
- Follow PEP 8 with four-space indents, snake_case modules/functions, CamelCase classes, and ALL_CAPS environment keys.
- Prefer explicit type hints and Pydantic models for request/response contracts, validating inputs at router boundaries.
- Group imports (stdlib, third-party, local) and avoid mixing synchronous and async flows inside one module.

## Testing Guidelines
- Co-locate unit tests near their feature area and name files `test_<scope>.py`; express test functions as `test_<expectation>_<condition>`.
- Use pytest markers from `pytest.ini` (`unit`, `integration`, `fastapi`, `security`, `slow`) to focus runs and keep slow Azure suites opt-in.
- Raise coverage whenever touching security-critical services and reproduce failing tests locally before opening a PR.

## Commit & Pull Request Guidelines
- Keep commits concise, imperative, and issue-aware (Chinese or English), e.g. `Improve Azure search retry logic (#42)`.
- PRs must summarize changes, list test commands (`pytest -m "not slow"`), call out Azure config updates, and attach UI screenshots plus resource links when relevant.

## Security & Configuration Tips
- Store secrets in `.env`; never commit credentials or generated `instance/` files. Use Azure Key Vault for shared secrets.
- Keep `cookies.txt` and captured logs out of history; scrub sensitive traces and rotate API keys if exposure is suspected.
