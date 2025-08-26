# Copilot Repository Instructions for `oxytcmri-legacy`

## General Guidelines
- **Language**: Python 3.12+, `src` layout (`oxytcmri/`).
- **Coding style**:
  - Type hints required everywhere.
  - Docstrings in **NumPy style**, in English.
  - Follow **PEP8**, enforce with `ruff` + `black`.
  - Run `mypy --strict` locally and in CI.
- **Commits & PRs**:
  - Use **Conventional Commits** (feat, fix, docs, chore, test).
  - Keep PRs small and focused (≤ ~400 lines of changes).
  - Always update or add tests for any new/changed code.
  - Update README/docs if CLI or user-facing behavior changes.

## Testing & Coverage
- **Framework**: `pytest`.
- Coverage target: **≥ 85%**.  
- Use `pytest-cov` in CI.  
- Unit tests: `oxytcmri/tests/unit/`  
- Integration tests: `oxytcmri/tests/integration/`  
- End-to-end tests: `oxytcmri/tests/end_to_end/`.

## Project Structure
- **Domain layer**: `oxytcmri/domain/` → entities, use_cases, ports.
- **Infrastructure**: `oxytcmri/infrastructure/` → CLI, gateways, settings, logger.
- **Interface**: `oxytcmri/interface/` → controllers, adapters, repositories.
- **Tests**: mirror the package structure.

Follow **Clean Architecture principles**:
- Domain logic must not depend on infrastructure or interface.
- Infrastructure and interface implement the ports defined in the domain.

## Dependencies
- Installed and locked with [`uv`](https://github.com/astral-sh/uv).
- Install: `make install` (runtime) / `make install-dev` (with dev tools).
- Keep dependencies minimal; prefer stdlib when possible.

## CLI
- Main entrypoint: `main.py` calls `oxytcmri.infrastructure.cli.command_line_interface()`.
- Any new feature exposed through CLI must provide:
  - `--help` usage examples.
  - At least one integration test in `tests/end_to_end`.

## Documentation
- Built with **MkDocs Material** (`make docs`).
- Any new module or function must include docstrings compatible with `mkdocstrings`.

## Definition of Done
- PR passes **CI** (`pytest`, `ruff`, `mypy`).
- Code covered by tests (≥ 85%).
- Style and architecture rules followed.
- Docs/README updated if user-facing changes.
