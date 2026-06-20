# 🤖 Executor Prompt — Personal GateKeeper

> Hand this prompt to the executor AI. It is self-contained.

---

You are implementing the **Personal GateKeeper**, a Python 3.11+ / FastAPI project located at `D:\ai-project\free models`.

## Authoritative sources
- **`docs/plan/IMPLEMENTATION_PLAN.md`** — the complete, authoritative spec. Every behavior, schema, value, and file path is defined there by section number (e.g. §5, §13).
- **`models-classification.md`** (project root) — source of truth for all model data.
- **`tasks/`** — the work, broken into ordered stages. Start at `tasks/00-INDEX.md`.

## How to work
1. Read `tasks/00-INDEX.md` first — it lists all tasks, their dependencies, and conventions.
2. Work through the tasks **strictly in numeric order** (01 → 19). Do not start a task until its dependencies (listed in its header and the index table) are complete.
3. For **each** task:
   - Open the task file and read its *Objective*, *Files to create/modify*, and *Detailed spec*.
   - Cross-check the referenced `IMPLEMENTATION_PLAN.md` sections — match values, schemas, and paths exactly.
   - Implement only what the task scopes. Respect *Out of scope* notes.
   - Before considering the task done, verify **every** *Acceptance criteria* checkbox yourself.
   - **Apply the `clean-code-guard` skill on the code you wrote for that task** before moving on. Fix anything it flags. Do not advance to the next task with unresolved `clean-code-guard` findings.
4. After finishing a task, briefly state which task is done, what files changed, and that `clean-code-guard` passed. Then proceed to the next task.

## Mandatory skills
- **`clean-code-guard`** — invoke it after implementing each task, on the code produced in that task. Treat its findings as blocking: resolve them before the next task.
- **`test-guard`** — after **all** tasks (01–19) are complete, invoke `test-guard` to validate the full implementation. Address everything it reports.

## Rules
- Do not invent model IDs, rate limits, base URLs, or schema fields — use exactly what `IMPLEMENTATION_PLAN.md` and `models-classification.md` specify.
- Never commit secrets. Use `.env.example`; real keys go only in a local `.env` (gitignored).
- Async throughout; type hints; one provider per file; lightweight deps only.
- If a task's spec is ambiguous or conflicts with the plan, stop and flag it rather than guessing.
- Do not delete or rewrite `docs/plan/IMPLEMENTATION_PLAN.md` or the `tasks/` files — they are needed for review.

## Definition of done
All 19 tasks implemented in order, each with `clean-code-guard` passing, the gateway runnable per `IMPLEMENTATION_PLAN.md` §22, and `test-guard` run and green at the end.

Begin with `tasks/00-INDEX.md`, then `tasks/01-project-scaffold.md`.
