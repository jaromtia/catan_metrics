# Lab 0 — Environment Setup

> **Goal:** A working Python + Node environment with a project scaffold and a clean first commit.
>
> **Branch:** none yet — this lab sets up `main`.

This is the only lab where setup commands are spelled out, because toolchain configuration is not the skill being assessed. Even so, you must understand *why* each piece exists — you will be asked about it in the demo.

---

## Background

You are building a full-stack application with two halves:

- A **Python backend** (domain logic, engine, storage, API).
- A **TypeScript/React frontend** (the browser UI).

They run as two processes during development and talk over HTTP/WebSocket.

---

## Prerequisites

### Knowledge Required
- Python 3.12+ (data structures, classes, functions, pattern matching)
- Basic JavaScript / TypeScript (variables, functions, async/await)
- HTML & CSS fundamentals
- Command-line basics (cd, ls, mkdir, running scripts)
- Git basics (clone, commit, push, branch)

### Tools to Install

```
Python 3.12 or newer  (required for match/case used throughout the engine)
Node.js 20 or newer   (includes npm)
uv                    (Python package manager — replaces pip/venv here)
Git
VS Code or any editor
```

Install `uv` (see [the uv docs](https://docs.astral.sh/uv/) for your OS).

---

## Specification

Your repository must end this lab with the following structure. The package layout is a **contract** — later labs import from these exact module paths, so create them now even though they are empty.

```
catan-companion/
├── catan/
│   ├── __init__.py
│   ├── domain/        constants.py geometry.py board.py state.py commands.py events.py
│   ├── engine/        validate.py reduce.py awards.py projections.py
│   ├── store/         event_store.py codec.py repository.py
│   ├── cli/           main.py parser.py render.py
│   └── api/           app.py
├── tests/
├── design/
├── web/               (created by Vite in Task 4)
├── pyproject.toml
└── README.md
```

Your `pyproject.toml` must satisfy these requirements:

- Project name `catan-companion`, version `0.1.0`, `requires-python >= 3.12`.
- Runtime dependencies: `fastapi`, `uvicorn[standard]`.
- A dev dependency group containing `pytest` and `httpx`.
- A console-script entry point named `catan` that points at `catan.cli.main:main`.
- A build backend (hatchling) configured to package the `catan` directory.
- A pytest configuration that points `testpaths` at `tests`.

Your Vite dev server must proxy `/api` (including WebSocket upgrades) to `http://localhost:8000`.

Your `.gitignore` must exclude at least: `__pycache__/`, `*.pyc`, `.venv/`, `*.db`, `.env`, `dist/`, `web/node_modules/`, `web/dist/`.

---

## Your Tasks

1. **Create the package skeleton.** Make the directories above and an empty `__init__.py` in every Python package directory.

   ```bash
   mkdir -p catan/{domain,engine,store,cli,api} tests design
   touch catan/__init__.py catan/domain/__init__.py catan/engine/__init__.py \
         catan/store/__init__.py catan/cli/__init__.py catan/api/__init__.py
   ```

2. **Write `pyproject.toml`** to meet the specification above, then run `uv sync`. This creates `.venv` and a lockfile automatically. You run everything with the `uv run` prefix (e.g. `uv run pytest`).

3. **Write `.gitignore`** per the specification.

4. **Scaffold the frontend.** Inside `web/`, run `npm create vite@latest . -- --template react-ts` then `npm install`. Then write `web/vite.config.ts` so the dev server proxies `/api` to the backend with WebSocket support enabled.

5. **Make the first commit** on `main` containing `pyproject.toml`, the lockfile, and `.gitignore`.

> **Why uv instead of pip?** `uv sync` installs all dependency groups in one command and keeps a `uv.lock` for reproducible installs. You never manually activate a venv — prefix commands with `uv run`.

---

## Git Workflow (applies to every later lab)

- Never work directly on `main`. Each lab gets its own branch: `lab-N-short-description`.
- Commit often; each commit is one small, complete thought.
- Commit messages explain **why**, not what.
- Before every commit: does it run? did I break a test? is the message a complete sentence?

---

## Checkpoint

- [ ] `uv sync` completes without errors
- [ ] `uv run pytest` reports "no tests collected"
- [ ] `uv run python -c "import catan; print('OK')"` prints `OK`
- [ ] `npm run dev` (in `web/`) opens the Vite default page at `localhost:5173`
- [ ] `.gitignore` prevents `__pycache__`, `.venv`, and `*.db` from being committed
- [ ] First commit is clean and contains no generated artifacts
