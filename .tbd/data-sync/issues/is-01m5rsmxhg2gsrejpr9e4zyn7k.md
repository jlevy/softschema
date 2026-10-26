---
type: is
id: is-01m5rsmxhg2gsrejpr9e4zyn7k
title: Confirm fast-uri 3.1.9 (cool-off exception) was not yanked after 2026-11-02
kind: task
status: open
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5v4505x0s8nc898036ey4wh
due_date: 2026-11-03T00:00:00.000Z
created_at: 2026-10-25T05:48:30.639Z
updated_at: 2026-10-26T03:31:29.423Z
---
`packages/typescript/package.json:70-72` overrides `fast-uri` to exactly `3.1.9`, a transitive dependency of `ajv`. The override clears seven advisories against the old 3.1.6 pin (CHANGELOG `## v0.9.0`, Security). npm published 3.1.9 at 2026-10-19T23:05:26Z, inside the repository's 14-day cool-off, so the owner installed it under an exception. The cool-off clears at 2026-11-02T23:05Z.

State on 2026-10-26: 3.1.9 is the `three` dist-tag (latest 3.x) and is not deprecated.

On or after 2026-11-03, run:

```
npm view fast-uri@3.1.9 deprecated
npm view fast-uri dist-tags
npm view fast-uri time --json
```

- If 3.1.9 is still published, not deprecated, and has no new advisory, close this bead with that evidence. The exception has then aged out, and nothing needs to change.
- If it was deprecated, unpublished, or superseded by a fix, move the override to the replacement once it clears the cool-off, refresh `bun.lock` with `--frozen-lockfile` checks, and run `bun audit`.
