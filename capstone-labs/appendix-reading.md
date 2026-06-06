# Appendix C — Recommended Reading

Because the labs do not hand you the implementation, the reading here matters more than in a guided tutorial — these are the references you will actually consult while figuring things out.

---

## Required Background

- [Python Dataclasses](https://docs.python.org/3/library/dataclasses.html) — read the whole page. Focus on `frozen=True` and `field(default_factory=...)`.
- [Python Enums](https://docs.python.org/3/library/enum.html) — focus on `str, Enum` (values are strings, not ints).
- [Python Pattern Matching](https://docs.python.org/3/reference/compound_stmts.html#the-match-statement) — `match`/`case`, used heavily in `validate()` and `reduce()`.
- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/) — complete "First Steps" through "Request Body" and "WebSockets".
- [React: Thinking in React](https://react.dev/learn/thinking-in-react) — the definitive mental model. Read before Lab 6.
- [TypeScript Handbook: Types](https://www.typescriptlang.org/docs/handbook/2/types-from-types.html) — interfaces, type aliases, union types.

---

## Deeper Reading

- [Hexagonal Grids Guide](https://www.redblobgames.com/grids/hexagons/) — Amit Patel's reference on hex math. Read before Lab 1.
- [Event Sourcing Explained](https://martinfowler.com/eaaDev/EventSourcing.html) — Martin Fowler's original article. Read before Lab 3.
- [Functional Core, Imperative Shell](https://www.destroyallsoftware.com/screencasts/catalog/functional-core-imperative-shell) — Gary Bernhardt's talk. The engine is the functional core; the API and CLI are the imperative shell.
- [The Twelve-Factor App](https://12factor.net/) — industry principles for deployable software. Factors III (config via env vars) and X (dev/prod parity) apply directly.

---

## Tools Reference

- [uv Documentation](https://docs.astral.sh/uv/) — the package manager used in this project.
- [SQLite Documentation](https://www.sqlite.org/lang.html) — SQL syntax reference (Lab 3).
- [MDN SVG Reference](https://developer.mozilla.org/en-US/docs/Web/SVG/Element) — every SVG element used in the board renderer (Lab 6).
- [pytest Documentation](https://docs.pytest.org/) — fixtures, `parametrize`, coverage (Lab 8).
- [Vite Configuration](https://vitejs.dev/config/) — dev-server proxy setup for `/api` (Lab 0).

---

## A Note on Looking Things Up

You are expected to research. Reading official docs, hex-math references, and event-sourcing articles is exactly what a working engineer does. What you should **not** do is copy a finished Catan implementation — the point of these labs is to derive the design yourself from the specification and the rules. If you get stuck, re-read the relevant lab's *Specification* and *Hints* sections and write a smaller test before reaching for someone else's code.
