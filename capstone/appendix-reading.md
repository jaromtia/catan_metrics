# Appendix C — Recommended Reading

---

## Required Background

- [Python Dataclasses](https://docs.python.org/3/library/dataclasses.html) — Official docs; read the whole page. Focus on `frozen=True` and `field(default_factory=...)`.
- [Python Enums](https://docs.python.org/3/library/enum.html) — Focus on `str, Enum` (values are strings, not ints).
- [Python Pattern Matching](https://docs.python.org/3/reference/compound_stmts.html#the-match-statement) — `match`/`case` syntax used heavily in `validate()` and `reduce()`.
- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/) — Complete "First Steps" through "Request Body" and "WebSockets".
- [React: Thinking in React](https://react.dev/learn/thinking-in-react) — The definitive mental model. Read before Phase 6.
- [TypeScript Handbook: Types](https://www.typescriptlang.org/docs/handbook/2/types-from-types.html) — Interfaces, type aliases, union types.

---

## Deeper Reading (for strong students)

- [Hexagonal Grids Guide](https://www.redblobgames.com/grids/hexagons/) — Amit Patel's definitive reference. Covers axial, cube, and offset coordinates with interactive demos. Read before Phase 1.
- [Event Sourcing Explained](https://martinfowler.com/eaaDev/EventSourcing.html) — Martin Fowler's original article.
- [Functional Core, Imperative Shell](https://www.destroyallsoftware.com/screencasts/catalog/functional-core-imperative-shell) — Gary Bernhardt's talk. The engine is the functional core; the API and CLI are the imperative shell.
- [The Twelve-Factor App](https://12factor.net/) — Industry-standard principles for deployable software. Factors III (config via env vars) and X (dev/prod parity) apply directly to this project.

---

## Tools Reference

- [uv Documentation](https://docs.astral.sh/uv/) — Package manager used in this project.
- [SQLite Documentation](https://www.sqlite.org/lang.html) — SQL syntax reference.
- [MDN SVG Reference](https://developer.mozilla.org/en-US/docs/Web/SVG/Element) — Every SVG element used in the board renderer.
- [pytest Documentation](https://docs.pytest.org/) — Fixtures, `parametrize`, coverage.
- [Vite Configuration](https://vitejs.dev/config/) — Dev server proxy setup for `/api`.

---

## Understanding This Codebase

Before diving in, read these files in order:

1. `docs/architecture.md` — understand the 4-layer structure
2. `catan/domain/constants.py` — the base Catan rules as typed constants
3. `catan/domain/geometry.py` — how the board topology is computed
4. `catan/engine/validate.py` — the `Result` type and validate dispatch
5. `tests/test_validate.py` — how the engine is tested
6. `catan/api/app.py` — how the engine is exposed over HTTP
