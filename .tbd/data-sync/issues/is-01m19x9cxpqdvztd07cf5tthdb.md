---
type: is
id: is-01m19x9cxpqdvztd07cf5tthdb
title: "[epic] repair as its own command, and strict reads"
kind: feature
status: open
priority: 1
version: 23
labels: []
dependencies:
  - type: blocks
    target: is-01m18tkzqtfq03b9rxp3y9gvde
child_order_hints:
  - is-01m19xagy48cpx37h2ph4d1w2g
  - is-01m19xahh31yvdk9arvvjt1qyp
  - is-01m19xaj0ps205t2s00bdnaejc
  - is-01m19xajct4hafm1daa780pfpj
  - is-01m19xb9dfm7nad0077a6v737h
  - is-01m19xb9s5nxjaxmmwqzt5e1r0
  - is-01m19xba51hdfg7gsrqksqy3ft
  - is-01m19xbaj4bbdahk5vw24pp568
  - is-01m19xbazge30zpc6wx7k50mpx
  - is-01m19xbbdmcv1rsdh9s0x2fpq3
  - is-01m19xc7rq9gevsfm3851bv56j
  - is-01m19xc84hfwfmk4a3xsfbw379
  - is-01m19xc8gqjq2nksc03y981jez
  - is-01m19xc8wxx69226wyka7144d2
  - is-01m19xc98q9wqw820dmj0py4ms
  - is-01m19xc9mgm0c8hstn7kc9dshd
  - is-01m19xca07vajnjj9f5p9sgy6c
  - is-01m19xcacbe2bz4n54qcjeh34c
  - is-01m19xcybzz5zcr27y96q1vq5w
  - is-01m19xcyqz1ddyrpe6jbc0g4xa
  - is-01m19xcz3ktm8yt7ajz1p5ww55
created_at: 2026-08-30T18:00:43.702Z
updated_at: 2026-08-30T18:02:54.139Z
---
Spec: docs/project/specs/active/plan-2026-08-30-repair-command.md

Three connected surface changes to the unreleased --repair feature, settled with the maintainer:

1. 'softschema repair' becomes its own command. --repair and --check-repair leave 'validate'.
   Before: validate --repair / validate --check-repair
   After:  repair / repair --dry-run / repair --check

2. Strict-versus-checking becomes a property of the command, not of which flags were passed.
   validate = consuming gate, read failure is exit 2 regardless of --contract.
   repair    = producing loop, read failure is a record at exit 1 regardless of binding.
   This closes two leaks that currently point in opposite directions.

3. Add load_artifact / loadArtifact: a strict consuming API that returns values and raises
   on anything short of valid. Today a consumer that forgets to check outcome gets
   values=None and a downstream TypeError.

Plus: mechanical enforcement that --check-repair cannot reappear outside historical review docs.

Do this before tagging v0.8.0 -- the feature is unreleased, so the surface is free to change now and expensive to change later.
