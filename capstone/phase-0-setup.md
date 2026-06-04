# Phase 0 — Environment Setup

> **Goal:** Working Python + Node environment with the project scaffold in place.

---

## Prerequisites

### Knowledge Required
- Python 3.12+ (data structures, classes, functions)
- Basic JavaScript / TypeScript (variables, functions, async/await)
- HTML & CSS fundamentals
- Command-line basics (cd, ls, mkdir, running scripts)
- Git basics (clone, commit, push, branch)

### Tools to Install

```
Python 3.12 or newer  (this project requires >=3.12 for pattern matching)
Node.js 20 or newer   (includes npm)
uv (Python package manager — replaces pip/venv in this project)
Git
VS Code or any editor
```

Install `uv`:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 0.1 Project Structure

```
catan-companion/
├── catan/
│   ├── __init__.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── constants.py
│   │   ├── geometry.py
│   │   ├── board.py
│   │   ├── state.py
│   │   ├── commands.py
│   │   └── events.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── validate.py
│   │   ├── reduce.py
│   │   ├── awards.py
│   │   └── projections.py
│   ├── store/
│   │   ├── __init__.py
│   │   ├── event_store.py
│   │   ├── codec.py
│   │   └── repository.py
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── parser.py
│   │   └── render.py
│   └── api/
│       ├── __init__.py
│       └── app.py
├── tests/
├── design/
├── web/          (created by Vite, see 0.3)
├── pyproject.toml
└── README.md
```

Create it:
```bash
mkdir -p catan/{domain,engine,store,cli,api}
mkdir -p tests design
touch catan/__init__.py
touch catan/domain/__init__.py catan/engine/__init__.py
touch catan/store/__init__.py catan/cli/__init__.py catan/api/__init__.py
```

---

## 0.2 Python Project Setup

Create `pyproject.toml`:

```toml
[project]
name = "catan-companion"
version = "0.1.0"
description = "Companion engine for tracking metrics during a physical game of Catan."
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.100",
    "uvicorn[standard]>=0.23",
]

[project.scripts]
catan = "catan.cli.main:main"

[dependency-groups]
dev = [
    "httpx>=0.28",
    "pytest>=8.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["catan"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Install and sync:
```bash
uv sync
```

This creates a `.venv` automatically. To run commands:
```bash
uv run python -c "import catan; print('OK')"
uv run pytest          # should say "no tests collected"
uv run catan --help    # should print usage once you implement cli/main.py
```

> **Why uv instead of pip?**
> `uv` is a modern, fast Python package manager. `uv sync` installs all deps (main + dev groups) in one command and keeps a `uv.lock` lockfile for reproducible installs. You never need to manually activate a venv — prefix every command with `uv run`.

Create `.gitignore`:
```
__pycache__/
*.pyc
.venv/
*.db
.env
dist/
web/node_modules/
web/dist/
```

---

## 0.3 Frontend Setup

```bash
cd web
npm create vite@latest . -- --template react-ts
npm install
```

This generates:
```
web/
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

Configure the dev proxy so Vite forwards `/api` to your Python server:

**`web/vite.config.ts`:**
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,   // enables WebSocket proxying
      }
    }
  }
})
```

Verify:
```bash
npm run dev   # should open the Vite default page at localhost:5173
```

---

## 0.4 Git Setup

```bash
git init
git add pyproject.toml uv.lock .gitignore
git commit -m "Initial project scaffolding"
```

### Branching Strategy

Never work directly on `main`. Create a branch for each phase:
```bash
git checkout -b phase-1-domain-models
# ... do work ...
git push origin phase-1-domain-models
# Open a pull request, merge, delete branch
```

**Branch naming:** `phase-N-short-description`

**Commit checklist:**
- Does the code run without errors?
- Did I break any existing tests?
- Is my commit message a complete sentence explaining WHY?

---

## 0.5 Verify Everything Works

```bash
# Python
uv run python -c "import catan; print('Python OK')"
uv run pytest

# Frontend
cd web && npm run dev
```

### Phase 0 Checkpoint

- [ ] `uv sync` completes without errors
- [ ] `uv run pytest` reports "no tests collected"
- [ ] `npm run dev` opens the Vite default page
- [ ] `.gitignore` prevents `__pycache__`, `.venv`, `*.db` from being committed
- [ ] First commit is clean
