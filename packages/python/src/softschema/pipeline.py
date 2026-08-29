"""Repair, conform, then validate — the one operation an agent and a gate both run.

Validation normally happens after the process that wrote the artifact has exited. By then
the session that could fix the document is gone, so a large, nearly-correct artifact is
discarded over a single field and the only recovery is regenerating the whole thing from a
cold prompt.

This module closes that gap by letting the producer run the same check its judge will run,
before it finishes. The escalating pass is:

1. Read the document.
2. Repair it, if it does not parse. Schema-free; see :mod:`softschema.repair`.
3. Conform its scalars to the types the contract declares. See :mod:`softschema.conform`.
4. Write once, if anything changed.
5. Validate, and report both the verdict and what was changed.

**One write, not two.** Repair hands its output to conform in memory rather than through
the filesystem. That is what makes idempotence and the minimal-diff property testable
rather than emergent, and it means a conform that has to back out cannot leave a
half-applied file behind.

**``validate_artifact`` stays read-only.** A function named ``validate_`` must not rewrite
the file its caller passed, and library callers depend on that. Writing is this module's
job, and only when asked.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from softschema._portable import PortableInputError, write_artifact_text
from softschema.conform import conform_artifact
from softschema.models import Contract, SchemaMetadata, SchemaProfile, parse_schema_metadata
from softschema.repair import RepairResult, repair_artifact
from softschema.validate import (
    ArtifactValidationResult,
    parse_frontmatter_text,
    parse_yaml_text,
    resolve_bound_schema,
    validate_artifact,
)


def repair_and_validate_artifact(
    doc_path: Path,
    *,
    contract: Contract,
    model: type[BaseModel] | None = None,
    write: bool = True,
    repaired: RepairResult | None = None,
) -> ArtifactValidationResult:
    """Repair and conform an artifact, then validate what results.

    ``repaired`` accepts a repair the caller already performed, so the CLI — which must
    repair before it can infer the contract binding out of the frontmatter — does not cause
    the work to happen twice.

    ``write=False`` is the check mode: everything is computed and reported, and the file is
    not touched. That is what a gate runs when it wants to know whether an artifact *would*
    be repaired without mutating one under review.

    The returned result carries a ``repairs`` list describing every change. It is the field
    that distinguishes "was already valid" from "was repaired into validity"; an exit code
    cannot say which happened.

    A repaired document is written even when it still fails validation afterward. The
    repair is independently correct — an unparsable file left on disk to preserve a
    failing verdict helps nobody — and the verdict is reported honestly either way.
    """
    profile = contract.profile
    # A caller that already ran repair — the CLI does, because binding inference needs the
    # repaired text — hands the result in rather than making the file be repaired twice.
    if repaired is None:
        repaired = repair_artifact(doc_path, profile=profile, write=False)
    records: list[dict[str, Any]] = list(repaired.records)
    text = repaired.text

    # Resolve the schema the way validation will, rather than reading `contract.schema_path`
    # directly: for a self-describing artifact that field is empty and the binding lives in
    # the document's own `softschema.schema`. Taking the shortcut here makes conform a
    # silent no-op for exactly the artifacts this feature exists to serve.
    conformed = conform_artifact(
        doc_path,
        schema_path=resolve_bound_schema(contract, doc_path, _document_metadata(text)),
        model=model if model is not None else contract.model,
        envelope_key=contract.envelope_key,
        profile=profile,
        write=False,
        text=text,
    )
    if conformed.changed:
        records.extend(conformed.records)
        text = conformed.text

    changed = bool(records)
    if changed and write and text is not None:
        write_artifact_text(doc_path, text)

    document, have_document = (None, False) if text is None else _reparse(text, profile)
    if have_document:
        result = validate_artifact(doc_path, contract=contract, document=document)
    else:
        # Nothing usable to hand over — the repair could not produce readable text, or
        # there was no text at all. Omitting `document` (rather than passing a sentinel of
        # our own that `validate_artifact` would mistake for a parsed root) makes
        # validation read the file itself and produce its own diagnostic, exactly as a
        # plain `validate` on the same artifact would.
        result = validate_artifact(doc_path, contract=contract)
    return _with_repairs(result, records)


def _document_metadata(text: str | None) -> SchemaMetadata | None:
    """The artifact's own ``softschema:`` block, for schema-binding resolution.

    Read from the post-repair text, because a document whose metadata block was itself
    unparsable before the repair still binds a schema afterward.
    """
    if text is None:
        return None
    try:
        _body, frontmatter = parse_frontmatter_text(text)
        if frontmatter is None:
            frontmatter = parse_yaml_text(text)
        if not isinstance(frontmatter, dict):
            return None
        return parse_schema_metadata(frontmatter.get("softschema"))
    except (PortableInputError, ValueError, ValidationError):
        # A malformed block is validation's to report; here it just means no binding.
        return None


def _reparse(text: str, profile: SchemaProfile) -> tuple[Any, bool]:
    """Parse the post-repair text the way validation would parse the file.

    Validation must judge what this pass produced, not what was on disk when it started.
    Handing it the pre-repair parse would report failures that were just fixed — and under
    ``write=False`` there is no repaired file to re-read, so the in-memory text is the only
    correct source.

    Returns ``(document, True)`` on success — where ``document`` may legitimately be
    ``None`` for a file with no frontmatter — and ``(None, False)`` when the text still
    does not parse, in which case the caller omits ``document`` entirely so validation
    reads the file and reports the failure itself. Both branches go through the same
    readers validation uses, so there is no second parse implementation here to drift from
    the first.
    """
    try:
        if profile is SchemaProfile.pure_yaml:
            return parse_yaml_text(text), True
        _body, frontmatter = parse_frontmatter_text(text)
    except PortableInputError:
        return None, False
    return frontmatter, True


def _with_repairs(
    result: ArtifactValidationResult, records: list[dict[str, Any]]
) -> ArtifactValidationResult:
    """Attach repair records to a validation result.

    ``replace`` rather than mutation keeps the frozen contract intact: ``outcome`` is
    ``init=False`` and is recomputed by ``__post_init__``, so the copy is complete.
    """
    return dataclasses.replace(result, repairs=records)
