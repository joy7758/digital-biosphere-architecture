# Lifecycle Profile RC1 Release Checklist

## Release order

1. Freeze and publish `agent-object-protocol`
2. Freeze and publish `aro-audit`
3. Update and publish the Digital Biosphere RC1 entry page
4. Post outward-facing notes in the selected channels

## Step-by-step

1. Confirm local state
Success: target repos are on the intended branch, tags point to the intended commits, and only expected paths are changed.

2. Push AOP commit and tag
Run: `git push origin feat/lifecycle-profile-v0.1 && git push origin lifecycle-profile-v0.1-rc1`
Success: tag `lifecycle-profile-v0.1-rc1` is visible on the remote and the RC1 release note path is reachable.

3. Draft the AOP release
Use `docs/releases/lifecycle-profile-v0.1-rc1.md` as the release body.
Success: release page clearly states scope, validation command, and known limitations.

4. Push ARO commit and tag
Run: `git push origin feat/lifecycle-profile-v0.1 && git push origin aro-lifecycle-conformance-rc1`
Success: tag `aro-lifecycle-conformance-rc1` is visible on the remote and the verifier command in the release note is still correct.

5. Draft the ARO release
Use `docs/releases/aro-lifecycle-conformance-rc1.md` as the release body.
Success: release page clearly states executable checks and tamper-evident boundary.

6. Publish the DBA entry and outward-facing posts
Success: the unified entry points to the final RC1 locations and the first public post links back to the canonical entries.

## Rollback if tag or release fails

- If a local tag points to the wrong commit: delete and recreate it before pushing.
- If a pushed tag is wrong: delete the remote tag, fix the local tag, then push again.
- If a release body is inaccurate: edit the release note file first, then update the remote release text.

## First feedback signals to watch

- whether readers use the name `Lifecycle Profile RC1`
- whether they cite the AOP or ARO canonical entry rather than an ad hoc commit link
- whether objections are about scope boundaries or about verifier semantics
- whether framework readers understand this as a lifecycle governance layer, not a new runtime
