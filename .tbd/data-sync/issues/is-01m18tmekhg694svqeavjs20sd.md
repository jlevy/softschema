---
type: is
id: is-01m18tmekhg694svqeavjs20sd
title: "Run release e2e phases 2-4: clean-environment installs and the quickstart as written"
kind: task
status: open
priority: 1
version: 2
labels: []
dependencies:
  - type: blocks
    target: is-01m18tmexsyfvna9mfce7ztnvj
parent_id: is-01m18tkzqtfq03b9rxp3y9gvde
created_at: 2026-08-30T07:55:05.713Z
updated_at: 2026-08-30T07:55:15.324Z
---
CI covers phase 1 and artifact smoke; it does not cover these. From the v0.8.0 readiness review's checklist:
- clean-environment install of the built wheel (uvx softschema@<version>) and the npm tarball (npx -y softschema@<version>)
- the README quickstart run verbatim: docs example-artifact, docs example-schema, validate
- the skill bootstrap (softschema skill --install) into a scratch repo

Blocked on the version bump and changelog cut, since the artifacts under test are built from the tagged tree.
