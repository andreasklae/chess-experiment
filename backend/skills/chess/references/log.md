# Wiki Log

Append-only record of every page created, updated, split, or promoted.
Newest first. One entry per maintenance action. Format:

```
## [YYYY-MM-DD] <op> | <page path> | <short description>
```

Ops: `create`, `update`, `split`, `promote` (draft→tested), `retire`.
This log plus `git diff` between batch SHAs is how the experiment measures
what the agent learned and when — keep it faithful.

---

## [2026-06-02] create | patterns/mating-patterns/back-rank-mate.md | First seed page — validates the page contract (frontmatter + When-to-use/Idea/What-to-do/Watch-out/Examples). FEN verified mate in python-chess. status: draft.

## [2026-06-02] create | (scaffold) | Initial wiki skeleton: top index, per-folder indexes, this log. No content pages yet.
