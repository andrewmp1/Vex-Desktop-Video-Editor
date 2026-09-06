# Superpowers in this repo

Development follows [Superpowers](https://github.com/obra/superpowers) skills:

1. **brainstorming** → spec in `docs/superpowers/specs/`
2. **writing-plans** → plan in `docs/superpowers/plans/`
3. **executing-plans** or **subagent-driven-development** → implement with TDD
4. **verification-before-completion** → fresh pytest before any “done” claim
5. **requesting-code-review** → review before merge

Constraints from [project-plan.md](../project-plan.md) still apply: UI talks only to `AgentClient` + protocol; no Windows; no Vex imports in `ui/`.
