---
type: is
id: is-01ksrzx0g5ckce8eh5xzxnjr2w
title: Expose softschema.__version__ and CLI --version flag
kind: task
status: closed
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies: []
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-29T04:29:25.380Z
updated_at: 2026-05-29T04:29:43.450Z
closed_at: 2026-05-29T04:29:43.450Z
close_reason: softschema/__init__.py exposes __version__ via importlib.metadata.version with a PackageNotFoundError fallback for non-installed source checkouts. cli.py wires 'softschema --version' through argparse action='version'.
---
Per python-modern-guidelines and python-cli-patterns: 'Expose the version at runtime with importlib.metadata.version("<pkg>")'. Import in softschema/__init__.py and add __version__ to __all__. Wire argparse parser with action='version' so 'softschema --version' prints 'softschema X.Y.Z'.
