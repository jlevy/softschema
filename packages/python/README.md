# softschema (Python)

Soft schemas: gradual, practical validation for Markdown/YAML artifacts that mix prose
and structured data—built for humans and coding agents.

This is the Python implementation of [softschema](https://github.com/jlevy/softschema),
published on [PyPI](https://pypi.org/project/softschema/). A fully synchronized
TypeScript implementation is also available on npm.

## Install

```bash
pip install softschema
# or:
uv add softschema
```

## Quick Start

```python
from pathlib import Path

from softschema import validate_artifact

# A self-describing artifact validates with no extra arguments; pass contract=,
# contract_id=, or registry= to bind a schema explicitly.
result = validate_artifact(Path("doc.md"))
```

Integrations that already own parsing and model execution can use the runtime-neutral
contract core. Python-specific adapters are also available from an explicit namespace:

```python
from softschema.core import normalize_portable_value, validate_contract_id
from softschema.runtime import validate_artifact
```

The package root remains compatible with existing imports.

Or from the command line:

```bash
softschema validate doc.md
softschema validate doc.yaml --profile pure-yaml
```

The default is `frontmatter-md`; `.yaml` and `.yml` never select `pure-yaml` implicitly.

## Documentation

- [softschema Guide](https://github.com/jlevy/softschema/blob/main/docs/softschema-guide.md):
  the full mental model and adoption playbooks
- [softschema Spec](https://github.com/jlevy/softschema/blob/main/docs/softschema-spec.md):
  the exact artifact format and validation rules
- [Installation](https://github.com/jlevy/softschema/blob/main/docs/installation.md):
  pinned vs zero-install, uv and Node setup
- [Repository](https://github.com/jlevy/softschema)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
