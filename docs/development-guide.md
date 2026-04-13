# Development Guide

## Purpose

This project is a practical, enterprise-oriented RAG prototype for internal knowledge search.
The goal is not only to "make RAG work", but to keep the codebase maintainable, testable, and
safe enough to evolve toward production-style usage.

## Startup

### Recommended local startup flow

1. Start Docker Desktop.
2. Start the local database.
3. Set the OpenAI API key in the current terminal session.
4. Start the FastAPI server.

```powershell
docker compose up -d
$env:OPENAI_API_KEY="sk-..."
uv run uvicorn app.main:app --reload
```

### Notes

- The database is provided by Docker Compose.
- The OpenAI API key is intentionally loaded from an environment variable instead of being stored in code.
- After restarting the PC, you will usually need to run the startup flow again.

## Testing

Testing for this project should be split into two categories.

### Deterministic tests

These should be verified with regular automated tests.

- API returns the expected status code.
- Documents are saved correctly.
- Chunks are created in the expected count/order.
- Retrieval returns `top_k` items.
- Response schemas contain required fields.
- Threshold and refusal behavior work as specified.

### AI quality evaluation

These are not strictly deterministic and should be evaluated with a dataset.

- Whether the expected chunk appears in top-k retrieval results.
- Whether the generated answer stays within the provided context.
- Whether the answer cites or aligns with the retrieved sources.
- Whether the system refuses to answer when evidence is weak.

### Practical testing policy

- Use `pytest` for unit and integration tests.
- Mock OpenAI calls in normal automated tests.
- Reserve real API calls for explicit end-to-end checks.
- Maintain a small retrieval evaluation set with expected questions and expected chunks.

## Safe Change Scope

### Usually safe to edit

- `app/`
- `tests/`
- `README.md`
- `docs/`
- `docker-compose.yml`
- `pyproject.toml`

### Edit carefully

- `app/models.py`
- `app/database.py`
- `app/schemas.py`

Reason:
These files affect schema, persistence, and API contracts.

### Do not commit or share

- Real API keys
- Real `.env` values
- Real internal company documents
- Personal information
- Production database connection information

## Coding Conventions

### Structure

- Keep API endpoints thin.
- Put business logic in `app/services/`.
- Keep schema definitions in `app/schemas.py`.
- Keep persistence definitions in `app/models.py`.

### Style

- Use type hints.
- Prefer clear, explicit function names.
- Avoid mixing routing, retrieval logic, and answer generation in one function.
- Keep constants centralized where practical.
- Prefer small, composable functions over large handlers.

### Reliability

- Avoid import-time side effects when possible.
- Keep external-service setup lazy or startup-scoped.
- Handle OpenAI and database failures explicitly.

## Deployment Considerations

### Configuration

- Use environment variables for secrets and runtime configuration.
- Do not hardcode API keys.
- Plan to move model names, thresholds, and DB URLs into centralized settings.

### Database

- `Base.metadata.create_all()` is acceptable for early local development.
- For production-style deployment, move to migration management such as Alembic.
- Changing embedding models usually requires re-embedding stored chunks.

### RAG-specific cautions

- Retrieval quality can drift as data grows.
- Thresholds should be validated against an evaluation set.
- Low-confidence answers should eventually be refused or escalated.
- Source visibility and access control must be considered before using real internal data.

## Important Files

### API entrypoint

- `app/main.py`

### Retrieval and generation logic

- `app/services/search_service.py`
- `app/services/ask_service.py`

### OpenAI integration

- `app/embeddings.py`

### Chunking logic

- `app/chunking.py`

### Database configuration and schema

- `app/database.py`
- `app/models.py`

### API request/response contracts

- `app/schemas.py`

### Local infrastructure and dependencies

- `docker-compose.yml`
- `pyproject.toml`
- `uv.lock`

## Suggested Next Improvements

1. Add `.env`-based settings loading.
2. Add deterministic tests for `/documents`, `/search`, and `/ask`.
3. Add threshold-based refusal behavior to `/ask`.
4. Add retrieval evaluation cases.
5. Add logging and error-handling policy.
