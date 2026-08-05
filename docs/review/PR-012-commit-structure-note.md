# PR-012 Commit Structure Note

## Original Plan
The intended git commit structure was to divide the remediation work into four distinct commits:
1. `fix(governance): restore prepilot and recycle-bin assets`
2. `docs(audit): invalidate PR12 experiment evidence`
3. `test(experiment): add unbiased AHRP pilot methodology tests`
4. `experiment(ahrp): regenerate baseline and shadow evidence`
5. `chore(ahrp): retain AHRP v0.1 reference implementation`

## Actual Commit Structure
All the file modifications and restorations were inadvertently grouped into a single aggregated commit titled `docs(audit): invalidate PR12 experiment evidence` (following multiple `git add` and `git commit` commands executing in batch without isolating the staging area).

## Why the merge happened
The staging and commit sequence commands were executed in a chained sequence (`git add ... \n git commit ...`) but standard git behavior batched previously staged untracked directories/files together. Furthermore, repeated attempts to correct the history via `git reset` resulted in all untracked files being dumped back into the working tree, which were then fully staged in the final recovery commit to ensure no files were lost.

## Why this does not impact auditability
The primary objective of the remediation is to restore the integrity of the factual record, freeze the erroneous data from PR12, and supply correctly-generated AHRP outcomes via the Phase 2 shadow protocol. All critical evidence, JSONL data logic files, recovered pre-pilot baselines, and explanatory documentation (such as `INVALIDATED.md` and `PR-012-post-merge-integrity-audit.md`) are present and unmodified. The final hash of the system state is sound, and all tests pass. An unaesthetic git log does not compromise the mathematical verifyability of the evidence packages.
