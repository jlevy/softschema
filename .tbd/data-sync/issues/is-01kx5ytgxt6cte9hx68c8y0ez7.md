---
type: is
id: is-01kx5ytgxt6cte9hx68c8y0ez7
title: Make conformance Pages promotion monotonic across absence and outages
kind: bug
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - conformance
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx5yth4h3th3jvhb4r7gevef
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:07:48.409Z
updated_at: 2026-07-10T13:10:40.417Z
closed_at: 2026-07-10T12:34:41.066Z
close_reason: Added a protected-main root namespace digest marker; predeploy allows true absence only before the marker and fails closed on later 404, outage, shrinkage, or changed index bytes.
---
The Pages predeploy gate treats all-404 as absent on every run, so an outage or administrative unpublish could reset a previously published v1 namespace and permit replacement bytes. Persist an independently reviewed promotion marker/digest, allow absence only before first promotion, and fail closed on later absence.
