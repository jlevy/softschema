"""Make an agent-authored document say the types its contract asks for.

YAML plain scalars carry no type marker: ``1850`` is an integer because of how the
characters look, not because anyone said so. A program serializing a known value never
hits this, because every YAML emitter quotes a string that would otherwise resolve to
something else. An agent writing the document by hand has no serializer in the path, so a
brand genuinely named ``1850`` arrives as an integer and fails a ``type: string``
contract.

This module puts the missing serializer back, and it borrows both halves rather than
reimplementing either:

- **The contract decides what is wrong.** The document is judged by the same validation
  that will judge it seconds later, and the only disagreement acted on is "a string
  belongs here and something else arrived". Everything else — a missing field, a wrong
  value, a shape mismatch — is reported under a different error and passes through
  untouched. There is no second opinion about the schema kept here to drift from the
  first.

- **The document's own serializer decides how to write it.** The frontmatter is loaded
  round-trip, the offending scalars are replaced with their own source text as strings,
  and the document is written back through that same emitter. Handing it ``"1850"`` is
  what makes it write ``'1850'``.

The result is one direction only — a scalar becomes a string where the contract asks for
one, and nothing else changes — and it is lossless, because the text comes from the
scalar as written (``1.10`` stays ``1.10``, ``007`` stays ``007``) rather than from
``str()`` of the parsed value.

**Both validation layers are read, not one.** softschema runs structural and semantic
validation independently, and the same defect has a spelling in each: JSON Schema reports
``{"validator": "type", "validator_value": "string"}`` and Pydantic reports
``string_type``. Which one is available depends entirely on how the caller bound the
contract, and neither covers the other's callers:

- The CLI flow binds a compiled schema and has no model at all, because ``--model``
  imports local code and is opt-in. Structural is the only source there.
- A host that registers contracts as Pydantic models with no ``schema_path`` gets
  ``skipped_reason="no_schema"`` from the structural layer. Semantic is the only source
  there.

Keying on one would silently do nothing for half the callers, so this reads whichever ran.

**Two notations do not survive being retyped**, and both are recorded in the shared
vectors: a boolean comes back canonically spelled (``True`` becomes ``'true'``), and an
integer's leading ``+`` is dropped (``+1_000`` becomes ``'1_000'``). Round-trip mode
remembers a scalar's notation in the value it hands back, and neither of those is part of
what it remembers. Recovering either means re-reading the source text by hand, which is
the string surgery this module exists to avoid, and neither is reachable for a name a
person would give something.
"""

from __future__ import annotations

from collections.abc import MutableMapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from softschema._portable import (
    PortableInputError,
    dump_round_trip,
    parse_yaml,
    round_trip_yaml,
    split_frontmatter,
    write_artifact_text,
)
from softschema.errors import fmt_value
from softschema.models import SchemaProfile

# One-directional: this module reads validation, and the combined repair-and-validate
# entry point lives in `softschema.pipeline`, so neither of these two imports the other.
from softschema.validate import validate_structural

CONFORM_KIND = "conform_applied"
"""``kind`` on every record this module emits, matching the repair pass's surface."""

_SCALAR_CONFORMED = "scalar_conformed"
"""``code`` for the one correction this module performs."""

_STRING_TYPE_ERROR = "string_type"
"""Pydantic's verdict for "a string belongs here and something else arrived"."""

# Scalar types a YAML document hands back that have a faithful written form.
#
# ``None`` is absent deliberately: a null is an absent value, not a notation accident, and
# stringifying one would invent data.
#
# The date and time types are absent for a reason specific to softschema. Reading through
# ``parse_yaml`` maps an implicit timestamp to a *string* already, and ``_check_value``
# rejects a host-native date outright as unportable — so a date never reaches validation
# as a date, and there is nothing here to correct. A round-trip load does construct one,
# which is exactly why they are excluded rather than merely unnecessary: conforming a date
# would write back a value the portable reader then refuses, turning a valid document into
# an invalid one.
_COERCIBLE = (bool, int, float)

# A defect can hide another: correcting a type can newly satisfy an `if`/`then`, `anyOf`,
# or `$ref` branch that did not previously apply, revealing errors the validator never
# reached. Three rounds is far more nesting than a real contract has, and the loop exits
# on the first round that changes nothing, so the common case costs one pass.
_MAX_ROUNDS = 3


@dataclass(frozen=True)
class ConformResult:
    """What one conform attempt did.

    ``skipped_reason`` is set when there was nothing to conform *against* — no schema and
    no model — rather than nothing to conform. The distinction matters: a caller that
    cannot tell the two apart reports a silent success for a pass that never ran.
    """

    changed: bool
    text: str | None = None
    records: list[dict[str, Any]] = field(default_factory=list)
    skipped_reason: str | None = None


def _record(path: Sequence[Any], before: str, after: str) -> dict[str, Any]:
    return {
        "kind": CONFORM_KIND,
        "code": _SCALAR_CONFORMED,
        "path": list(path),
        "message": f"conformed {before} to the string {after}",
    }


def _scalar_text(yaml: Any, value: object) -> str:
    """The text the serializer itself would emit for this scalar.

    Round-trip scalar types remember their notation and the representer is the component
    that reconstructs it, so ask it for the node: ``1.10`` comes back as ``"1.10"``,
    ``007`` as ``"007"``, ``0x1F`` as ``"0x1F"``. ``str()`` collapses all three.
    """
    representer = yaml.representer
    node = representer.represent_data(value)
    # ``represent_data`` is normally reached through ``represent``, which clears this
    # bookkeeping when the document is done. Reaching it directly does not, so a value
    # merely inspected here would still be registered as already-represented when the real
    # dump runs, and could be emitted as an alias to a node no longer in the tree.
    representer.represented_objects.clear()
    representer.object_keeper.clear()
    representer.alias_key = None
    return str(node.value)


def _node_at(root: Any, loc: Sequence[Any]) -> tuple[Any, Any] | None:
    """The container and key holding the value at *loc*, or ``None`` if unreachable.

    ``loc`` is a validation error's location: a path of mapping keys and sequence indices.
    Anything that does not resolve means no edit, never a wrong one.
    """
    if not loc:
        return None
    node = root
    for step in loc[:-1]:
        if (isinstance(node, MutableMapping) and step in node) or (
            isinstance(node, list) and isinstance(step, int) and 0 <= step < len(node)
        ):
            node = node[step]
        else:
            return None
    key = loc[-1]
    if isinstance(node, MutableMapping) and key in node:
        return node, key
    if isinstance(node, list) and isinstance(key, int) and 0 <= key < len(node):
        return node, key
    return None


def _admits_string(validator_value: Any) -> bool:
    """Whether a JSON Schema ``type`` keyword asks for a string."""
    if isinstance(validator_value, str):
        return validator_value == "string"
    if isinstance(validator_value, list):
        return "string" in validator_value
    return False


def _structural_locations(values: Any, schema_path: Path) -> list[Sequence[Any]]:
    """Where the compiled schema wanted a string and got something else."""
    result = validate_structural(values, schema_path)
    return [
        record["path"]
        for record in result.errors
        if record.get("validator") == "type" and _admits_string(record.get("validator_value"))
    ]


def _semantic_locations(model: type[BaseModel], values: Any) -> list[Sequence[Any]]:
    """Where the model wanted a string and got something else.

    Everything the model reports under any other error type is a real disagreement with
    the contract and is left alone to fail.
    """
    try:
        model.model_validate(values)
    except ValidationError as exc:
        return [error["loc"] for error in exc.errors() if error["type"] == _STRING_TYPE_ERROR]
    except Exception:  # a model we cannot run is one we cannot apply
        # A contract model is downstream code and a validator of its own can raise
        # anything. This pass is an optimization on the way to validation, which runs next
        # and owns reporting the failure, so a model that will not run turns the pass off
        # for this artifact rather than taking the step down.
        return []
    return []


def _conform_values(
    values: Any,
    yaml: Any,
    *,
    schema_path: Path | None,
    model: type[BaseModel] | None,
) -> list[dict[str, Any]]:
    """Replace mistyped scalars with their own text. Returns one record per change."""
    records: list[dict[str, Any]] = []
    for _round in range(_MAX_ROUNDS):
        locations: list[Sequence[Any]] = []
        if schema_path is not None:
            locations.extend(_structural_locations(values, schema_path))
        if model is not None:
            locations.extend(_semantic_locations(model, values))
        if not locations:
            break
        changed_this_round = False
        for loc in locations:
            found = _node_at(values, loc)
            if found is None:
                continue
            container, key = found
            value = container[key]
            if not isinstance(value, _COERCIBLE):
                continue
            text = _scalar_text(yaml, value)
            # A plain str: the emitter quotes it if its text would otherwise resolve as
            # something else, which is the serializer doing the one job this module exists
            # to reinstate.
            container[key] = text
            records.append(_record(loc, fmt_value(value), fmt_value(text)))
            changed_this_round = True
        if not changed_this_round:
            break
    return records


def conform_artifact(
    path: Path,
    *,
    schema_path: Path | None = None,
    model: type[BaseModel] | None = None,
    envelope_key: str | None = None,
    profile: SchemaProfile = SchemaProfile.frontmatter_md,
    write: bool = True,
    text: str | None = None,
) -> ConformResult:
    """Conform one artifact's scalars to the string type its contract declares.

    ``schema_path`` and ``model`` are the two sources of truth; supply either or both.
    With neither there is nothing to conform against, and the result says so through
    ``skipped_reason`` rather than reporting an untouched document as a success.

    ``envelope_key`` names the key the payload lives under. ``None`` means the contract
    describes the document root.

    ``text`` lets a caller that already has the document (a repair pass, for instance)
    hand it over instead of paying for a second read — which is also what keeps the two
    passes to a single write.
    """
    if schema_path is None and model is None:
        return ConformResult(changed=False, text=text, skipped_reason="no_contract_binding")

    if text is None:
        try:
            # `newline=""` keeps the file's own line endings out of the read, so a CRLF
            # document is not silently reflowed to LF by the write-back.
            with path.open(encoding="utf-8", newline="") as handle:
                text = handle.read()
        except OSError:
            return ConformResult(changed=False, skipped_reason="artifact_unreadable")

    crlf = "\r\n" in text
    normalized = text.replace("\r\n", "\n") if crlf else text

    if profile is SchemaProfile.pure_yaml:
        region, prefix, suffix = normalized, "", ""
    else:
        split = split_frontmatter(normalized)
        if split is None:
            return ConformResult(changed=False, text=text, skipped_reason="no_frontmatter")
        region = split.metadata_text
        prefix = normalized[: split.metadata_offset]
        suffix = normalized[split.metadata_end :]

    yaml = round_trip_yaml()
    try:
        document = yaml.load(region)
    except Exception:
        return ConformResult(changed=False, text=text, skipped_reason="unparsable")
    if not isinstance(document, MutableMapping):
        return ConformResult(changed=False, text=text, skipped_reason="not_a_mapping")

    values = document if envelope_key is None else document.get(envelope_key)
    if not isinstance(values, MutableMapping):
        # A missing or non-mapping envelope is a real disagreement for validation to
        # report, not licence to apply the envelope's contract to the document root.
        return ConformResult(changed=False, text=text, skipped_reason="no_envelope")

    records = _conform_values(values, yaml, schema_path=schema_path, model=model)
    if not records:
        return ConformResult(changed=False, text=text)

    conformed = prefix + dump_round_trip(yaml, document) + suffix
    if crlf:
        conformed = conformed.replace("\n", "\r\n")

    # The portable round-trip guard: never write a value the reader would then reject. A
    # conform that cannot survive its own reader is worse than no conform, because it
    # turns a document that failed one field into a document that fails to parse.
    if not _still_portable(conformed, profile):
        return ConformResult(changed=False, text=text, skipped_reason="not_portable")

    if write:
        write_artifact_text(path, conformed)
    return ConformResult(changed=True, text=conformed, records=records)


def _still_portable(text: str, profile: SchemaProfile) -> bool:
    """Whether the conformed document still reads under the portable rules."""
    if profile is SchemaProfile.pure_yaml:
        region: str | None = text
    else:
        split = split_frontmatter(text.replace("\r\n", "\n"))
        region = None if split is None else split.metadata_text
    if region is None:
        return False
    try:
        parse_yaml(region)
    except PortableInputError:
        return False
    return True
