"""Apply ``status: enforced`` undeclared-property rules to Draft 2020-12 schemas.

The enforced policy is deliberately narrower than arbitrary JSON Schema. It prepares
the root schema and every supplied resource as one offline graph, resolves the supported
``$ref`` forms, and rejects a present object property when no successful applicable
schema evaluates its value. The implementation calls insertion of that local rule
``closure`` and performs it only where annotation flow makes the transformation
semantics-preserving.

Design rationale and counterexamples:
``docs/project/research/research-2026-08-23-json-schema-composition-and-enforcement.md``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import unquote, urldefrag, urljoin, urlparse

_ROOT_RETRIEVAL_URI = "https://softschema.invalid/__root__"

_NAME_MAP_KEYWORDS = frozenset(
    {"properties", "$defs", "definitions", "patternProperties", "dependentSchemas"}
)
_SCHEMA_LIST_KEYWORDS = frozenset({"anyOf", "oneOf", "allOf", "prefixItems"})
_SCHEMA_KEYWORDS = frozenset(
    {
        "items",
        "additionalProperties",
        "unevaluatedProperties",
        "unevaluatedItems",
        "not",
        "if",
        "then",
        "else",
        "contains",
        "propertyNames",
        "contentSchema",
    }
)
_DEFINITION_KEYWORDS = frozenset({"$defs", "definitions"})
_IN_PLACE_MAP_KEYWORDS = frozenset({"dependentSchemas"})
_IN_PLACE_LIST_KEYWORDS = frozenset({"allOf", "anyOf", "oneOf"})
_IN_PLACE_SINGLE_KEYWORDS = frozenset({"if", "then", "else", "not"})
_ANNOTATING_IN_PLACE_KEYWORDS = (
    _IN_PLACE_MAP_KEYWORDS | _IN_PLACE_LIST_KEYWORDS | (_IN_PLACE_SINGLE_KEYWORDS - {"not"})
)
_EXPLICIT_CLOSURE_KEYWORDS = frozenset({"additionalProperties", "unevaluatedProperties"})
_CONTEXT_SENSITIVE_REFERENCE_KEYWORDS = (
    _IN_PLACE_MAP_KEYWORDS
    | _IN_PLACE_LIST_KEYWORDS
    | _IN_PLACE_SINGLE_KEYWORDS
    | frozenset({"contains"})
)
_REFERENCE_NONVALIDATION_SIBLINGS = frozenset(
    {
        "$anchor",
        "$comment",
        "$defs",
        "$id",
        "$schema",
        "default",
        "definitions",
        "deprecated",
        "description",
        "examples",
        "readOnly",
        "title",
        "writeOnly",
    }
)

_FragmentContext = Literal["same_instance", "nested_instance"] | None


class EnforcementUnsupportedError(ValueError):
    """The checked enforced profile cannot prove a safe closure placement."""

    def __init__(self, reason: str, message: str, *, schema_path: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.schema_path = schema_path


class SchemaGraphError(ValueError):
    """The supplied root/resources do not form a valid offline schema graph."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class PreparedSchemaGraph:
    """Root and supplied resources after applying the checked enforced profile."""

    root: dict[str, Any]
    resources: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class _NodeInfo:
    base_uri: str
    resource_uri: str
    pointer: str
    path: tuple[str | int, ...]
    reusable_root: bool
    embedded_direct_resource: bool


def _pointer_token(value: str | int) -> str:
    return str(value).replace("~", "~0").replace("/", "~1")


def _append_pointer(pointer: str, *parts: str | int) -> str:
    suffix = "/".join(_pointer_token(part) for part in parts)
    return f"{pointer}/{suffix}" if suffix else pointer


def _display_path(path: tuple[str | int, ...]) -> str:
    return "#" + _append_pointer("", *path)


def _normalize_uri(uri: str) -> str:
    base, fragment = urldefrag(uri)
    return f"{base}#{unquote(fragment)}" if fragment else base


def _resolve_uri(base_uri: str, reference: str) -> str:
    if reference.startswith("#"):
        return _normalize_uri(f"{urldefrag(base_uri)[0]}{reference}")
    if urlparse(reference).scheme:
        return _normalize_uri(reference)
    resolved = urljoin(base_uri, reference)
    if not urlparse(resolved).scheme:
        raise SchemaGraphError(
            "reference",
            f"relative reference {reference!r} cannot be resolved against {base_uri!r}",
        )
    return _normalize_uri(resolved)


class _SchemaGraph:
    def __init__(
        self,
        root: dict[str, Any],
        resources: Mapping[str, dict[str, Any]],
    ) -> None:
        self.targets: dict[str, Any] = {}
        self.resource_roots: dict[str, Any] = {}
        self.infos: dict[int, _NodeInfo] = {}
        self.nodes: dict[int, dict[str, Any]] = {}
        self.inferred_closures: set[int] = set()
        # Cache only positive reachability; a cycle back-edge can make an interim false
        # result path-dependent while the outer traversal is still in progress.
        self.closure_reachable: set[int] = set()
        self._visit(
            root,
            base_uri=_ROOT_RETRIEVAL_URI,
            resource_uri=_ROOT_RETRIEVAL_URI,
            pointer="",
            path=(),
            reusable_root=False,
            main_root=True,
        )
        for key, resource in resources.items():
            if not urlparse(key).scheme or urldefrag(key)[1]:
                raise SchemaGraphError(
                    "resource_identity",
                    f"supplied resource key must be an absolute URI without a fragment: {key!r}",
                )
            initial_uri = _normalize_uri(key)
            declared_id = resource.get("$id")
            if isinstance(declared_id, str):
                resolved_id = urldefrag(_resolve_uri(initial_uri, declared_id))[0]
                if resolved_id != urldefrag(initial_uri)[0]:
                    raise SchemaGraphError(
                        "resource_identity",
                        f"supplied resource $id {declared_id!r} does not match its key {key!r}",
                    )
            self._visit(
                resource,
                base_uri=initial_uri,
                resource_uri=urldefrag(initial_uri)[0],
                pointer="",
                path=("resources", key),
                reusable_root=True,
                main_root=False,
            )
        self._check_reference_targets()

    def _register_target(self, uri: str, node: Any) -> None:
        normalized = _normalize_uri(uri)
        previous = self.targets.get(normalized)
        if previous is not None and previous is not node:
            raise SchemaGraphError("resource_identity", f"duplicate schema target identity: {uri}")
        self.targets[normalized] = node

    def _register_resource(self, uri: str, node: Any) -> None:
        normalized = urldefrag(_normalize_uri(uri))[0]
        previous = self.resource_roots.get(normalized)
        if previous is not None and previous is not node:
            raise SchemaGraphError(
                "resource_identity", f"duplicate schema resource identity: {normalized}"
            )
        self.resource_roots[normalized] = node
        self._register_target(normalized, node)
        self._register_target(f"{normalized}#", node)

    def _visit(
        self,
        node: Any,
        *,
        base_uri: str,
        resource_uri: str,
        pointer: str,
        path: tuple[str | int, ...],
        reusable_root: bool,
        main_root: bool,
    ) -> None:
        if isinstance(node, dict) and id(node) in self.infos:
            previous = self.infos[id(node)]
            raise SchemaGraphError(
                "shared_subschema",
                f"schema object at {_display_path(path)} is shared with "
                f"{_display_path(previous.path)}; deep-copy shared subschemas before validation",
            )
        self._register_target(f"{resource_uri}#{pointer}", node)
        if not isinstance(node, dict):
            return

        node_base = base_uri
        node_resource = resource_uri
        node_pointer = pointer
        node_reusable = reusable_root
        embedded_direct_resource = False
        resource_id = node.get("$id")
        if isinstance(resource_id, str):
            node_base = _resolve_uri(base_uri, resource_id)
            node_resource = urldefrag(node_base)[0]
            node_pointer = ""
            embedded_direct_resource = not main_root and not reusable_root
            node_reusable = reusable_root or not main_root
            self._register_resource(node_resource, node)
        elif pointer == "":
            self._register_resource(resource_uri, node)

        if "$dynamicRef" in node or "$dynamicAnchor" in node:
            raise EnforcementUnsupportedError(
                "dynamic_reference",
                "the enforced profile does not support $dynamicRef or $dynamicAnchor",
                schema_path=_display_path(path),
            )

        self.infos[id(node)] = _NodeInfo(
            base_uri=node_base,
            resource_uri=node_resource,
            pointer=node_pointer,
            path=path,
            reusable_root=node_reusable,
            embedded_direct_resource=embedded_direct_resource,
        )
        self.nodes[id(node)] = node
        anchor = node.get("$anchor")
        if isinstance(anchor, str):
            self._register_target(f"{node_resource}#{anchor}", node)

        for key, value in node.items():
            if key in _NAME_MAP_KEYWORDS and isinstance(value, dict):
                for name, child in value.items():
                    child_reusable = key in _DEFINITION_KEYWORDS
                    self._visit(
                        child,
                        base_uri=node_base,
                        resource_uri=node_resource,
                        pointer=_append_pointer(node_pointer, key, name),
                        path=(*path, key, name),
                        reusable_root=child_reusable,
                        main_root=False,
                    )
            elif key in _SCHEMA_LIST_KEYWORDS and isinstance(value, list):
                for index, child in enumerate(value):
                    self._visit(
                        child,
                        base_uri=node_base,
                        resource_uri=node_resource,
                        pointer=_append_pointer(node_pointer, key, index),
                        path=(*path, key, index),
                        reusable_root=False,
                        main_root=False,
                    )
            elif key in _SCHEMA_KEYWORDS and isinstance(value, dict | bool):
                self._visit(
                    value,
                    base_uri=node_base,
                    resource_uri=node_resource,
                    pointer=_append_pointer(node_pointer, key),
                    path=(*path, key),
                    reusable_root=False,
                    main_root=False,
                )

    def resolve_ref(self, node: dict[str, Any], reference: str) -> Any:
        info = self.infos[id(node)]
        uri = _resolve_uri(info.base_uri, reference)
        target = self.targets.get(uri)
        if target is None and "#" not in uri:
            target = self.targets.get(f"{uri}#")
        if target is None:
            raise SchemaGraphError("reference", f"unresolved reference: {reference}")
        return target

    def declares_properties(self, node: Any, seen: frozenset[int] | None = None) -> bool:
        if not isinstance(node, dict):
            return False
        if seen is None:
            seen = frozenset()
        properties = node.get("properties")
        patterns = node.get("patternProperties")
        if isinstance(properties, dict) or (isinstance(patterns, dict) and bool(patterns)):
            return True
        marker = id(node)
        if marker in seen:
            return False
        next_seen = seen | {marker}
        reference = node.get("$ref")
        if isinstance(reference, str) and self.declares_properties(
            self.resolve_ref(node, reference), next_seen
        ):
            return True
        for key in _IN_PLACE_LIST_KEYWORDS:
            value = node.get(key)
            if isinstance(value, list) and any(
                self.declares_properties(child, next_seen) for child in value
            ):
                return True
        dependent = node.get("dependentSchemas")
        if isinstance(dependent, dict) and any(
            self.declares_properties(child, next_seen) for child in dependent.values()
        ):
            return True
        conditional_keys = ("then", "else") if "if" in node else ()
        return any(self.declares_properties(node.get(key), next_seen) for key in conditional_keys)

    def _property_evaluators(
        self,
        node: Any,
        *,
        include_alternatives: bool,
        include_conditionals: bool,
        seen: frozenset[int] | None = None,
    ) -> tuple[set[str], set[str], bool]:
        """Collect same-instance property evaluators for conservative support checks."""
        if not isinstance(node, dict):
            return set(), set(), False
        if seen is None:
            seen = frozenset()
        if id(node) in seen:
            return set(), set(), False
        next_seen = seen | {id(node)}
        properties = node.get("properties")
        patterns = node.get("patternProperties")
        names = set(properties) if isinstance(properties, dict) else set()
        pattern_names = set(patterns) if isinstance(patterns, dict) else set()
        wildcard = any(key in node for key in _EXPLICIT_CLOSURE_KEYWORDS)

        children: list[Any] = []
        reference = node.get("$ref")
        if isinstance(reference, str):
            children.append(self.resolve_ref(node, reference))
        all_of = node.get("allOf")
        if isinstance(all_of, list):
            children.extend(all_of)
        if include_alternatives:
            for key in ("anyOf", "oneOf"):
                value = node.get(key)
                if isinstance(value, list):
                    children.extend(value)
            dependent = node.get("dependentSchemas")
            if isinstance(dependent, dict):
                children.extend(dependent.values())
        if include_conditionals and "if" in node:
            children.extend(node.get(key) for key in ("if", "then", "else"))

        for child in children:
            child_names, child_patterns, child_wildcard = self._property_evaluators(
                child,
                include_alternatives=include_alternatives,
                include_conditionals=include_conditionals,
                seen=next_seen,
            )
            names.update(child_names)
            pattern_names.update(child_patterns)
            wildcard = wildcard or child_wildcard
        return names, pattern_names, wildcard

    def _conditional_matcher_evaluators(
        self, node: Any, seen: frozenset[int] | None = None
    ) -> tuple[set[str], set[str], bool]:
        """Collect evaluators contributed by condition matchers at one instance site."""
        if not isinstance(node, dict):
            return set(), set(), False
        if seen is None:
            seen = frozenset()
        if id(node) in seen:
            return set(), set(), False
        next_seen = seen | {id(node)}
        names: set[str] = set()
        patterns: set[str] = set()
        wildcard = False
        matcher = node.get("if")
        if matcher is not None:
            names, patterns, wildcard = self._property_evaluators(
                matcher,
                include_alternatives=True,
                include_conditionals=True,
            )

        children: list[Any] = []
        reference = node.get("$ref")
        if isinstance(reference, str):
            children.append(self.resolve_ref(node, reference))
        for key in _IN_PLACE_LIST_KEYWORDS:
            value = node.get(key)
            if isinstance(value, list):
                children.extend(value)
        dependent = node.get("dependentSchemas")
        if isinstance(dependent, dict):
            children.extend(dependent.values())
        if "if" in node:
            children.extend(node.get(key) for key in ("then", "else"))

        for child in children:
            child_names, child_patterns, child_wildcard = self._conditional_matcher_evaluators(
                child, next_seen
            )
            names.update(child_names)
            patterns.update(child_patterns)
            wildcard = wildcard or child_wildcard
        return names, patterns, wildcard

    def _condition_matchers_are_covered(self, node: dict[str, Any]) -> bool:
        matcher_names, matcher_patterns, matcher_wildcard = self._conditional_matcher_evaluators(
            node
        )
        if not matcher_names and not matcher_patterns and not matcher_wildcard:
            return True
        covered_names, covered_patterns, covered_wildcard = self._property_evaluators(
            node,
            include_alternatives=False,
            include_conditionals=False,
        )
        if matcher_wildcard and not covered_wildcard:
            return False
        for name in matcher_names:
            if name in covered_names or any(
                re.search(pattern, name) for pattern in covered_patterns
            ):
                continue
            return False
        return matcher_patterns <= covered_patterns

    def _evaluates_object_properties(self, node: Any) -> bool:
        names, patterns, wildcard = self._property_evaluators(
            node,
            include_alternatives=True,
            include_conditionals=True,
        )
        return bool(names or patterns or wildcard)

    def _check_child_evaluator_overlaps(self, node: dict[str, Any]) -> None:
        """Refuse sibling child applicators whose independent closure can conflict."""
        contains = node.get("contains")
        if self._evaluates_object_properties(contains):
            item_schemas: list[tuple[str, Any]] = []
            if "items" in node:
                item_schemas.append(("items", node["items"]))
            prefix_items = node.get("prefixItems")
            if isinstance(prefix_items, list):
                item_schemas.extend(
                    (f"prefixItems/{index}", child) for index, child in enumerate(prefix_items)
                )
            for keyword, child in item_schemas:
                if self._evaluation_reaches_inferred_closure(child):
                    raise EnforcementUnsupportedError(
                        "child_evaluator_overlap",
                        f"contains and {keyword} can evaluate the same array element; "
                        "make closure explicit at every affected structured descendant "
                        "or separate the item and match criteria",
                        schema_path=_display_path(self.infos[id(node)].path),
                    )

        properties = node.get("properties")
        patterns = node.get("patternProperties")
        property_entries = list(properties.items()) if isinstance(properties, dict) else []
        pattern_entries = list(patterns.items()) if isinstance(patterns, dict) else []
        for name, property_schema in property_entries:
            for pattern, pattern_schema in pattern_entries:
                if (
                    re.search(pattern, name)
                    and self._evaluates_object_properties(property_schema)
                    and self._evaluates_object_properties(pattern_schema)
                    and (
                        self._evaluation_reaches_inferred_closure(property_schema)
                        or self._evaluation_reaches_inferred_closure(pattern_schema)
                    )
                ):
                    raise EnforcementUnsupportedError(
                        "child_evaluator_overlap",
                        f"property {name!r} is also matched by patternProperties pattern "
                        f"{pattern!r}; make closure explicit at every affected structured "
                        "descendant in both value schemas or separate their property domains",
                        schema_path=_display_path(self.infos[id(node)].path),
                    )

        for index, (first_pattern, first_schema) in enumerate(pattern_entries):
            for second_pattern, second_schema in pattern_entries[index + 1 :]:
                if (
                    self._evaluates_object_properties(first_schema)
                    and self._evaluates_object_properties(second_schema)
                    and (
                        self._evaluation_reaches_inferred_closure(first_schema)
                        or self._evaluation_reaches_inferred_closure(second_schema)
                    )
                ):
                    raise EnforcementUnsupportedError(
                        "child_evaluator_overlap",
                        "structured patternProperties value schemas may evaluate the same "
                        f"property ({first_pattern!r} and {second_pattern!r}); make closure "
                        "explicit at every affected structured descendant in both value "
                        "schemas or use one structured pattern",
                        schema_path=_display_path(self.infos[id(node)].path),
                    )

    def _check_reference_targets(self) -> None:
        for marker, info in self.infos.items():
            node = self.nodes[marker]
            reference = node.get("$ref")
            if not isinstance(reference, str):
                continue
            target = self.resolve_ref(node, reference)
            target_info = self.infos.get(id(target))
            if (
                target_info is not None
                and not target_info.reusable_root
                and not _has_explicit_closure(target)
                and self.declares_properties(target)
            ):
                raise EnforcementUnsupportedError(
                    "reference_target_context",
                    "a structured $ref target is also applied directly; move it to $defs "
                    "or a supplied resource",
                    schema_path=_display_path(info.path),
                )

    def _evaluation_reaches_inferred_closure(
        self,
        node: Any,
        seen: frozenset[int] | None = None,
    ) -> bool:
        if not isinstance(node, dict):
            return False
        if seen is None:
            seen = frozenset()
        marker = id(node)
        if marker in self.closure_reachable:
            return True
        if marker in seen:
            return False
        if marker in self.inferred_closures:
            self.closure_reachable.add(marker)
            return True
        next_seen = seen | {marker}
        reference = node.get("$ref")
        if isinstance(reference, str) and self._evaluation_reaches_inferred_closure(
            self.resolve_ref(node, reference), next_seen
        ):
            self.closure_reachable.add(marker)
            return True
        for key, value in node.items():
            if key in _DEFINITION_KEYWORDS:
                continue
            if key in _NAME_MAP_KEYWORDS and isinstance(value, dict):
                if any(
                    self._evaluation_reaches_inferred_closure(child, next_seen)
                    for child in value.values()
                ):
                    self.closure_reachable.add(marker)
                    return True
            elif key in _SCHEMA_LIST_KEYWORDS and isinstance(value, list):
                if any(
                    self._evaluation_reaches_inferred_closure(child, next_seen) for child in value
                ):
                    self.closure_reachable.add(marker)
                    return True
            elif key in _SCHEMA_KEYWORDS and self._evaluation_reaches_inferred_closure(
                value, next_seen
            ):
                self.closure_reachable.add(marker)
                return True
        return False

    @staticmethod
    def _reference_has_validation_siblings(node: dict[str, Any]) -> bool:
        return any(key != "$ref" and key not in _REFERENCE_NONVALIDATION_SIBLINGS for key in node)

    def _check_context_sensitive_references(
        self,
        node: Any,
        composition_context: bool = False,
    ) -> None:
        if not isinstance(node, dict):
            return
        reference = node.get("$ref")
        if (
            (composition_context or self._reference_has_validation_siblings(node))
            and isinstance(reference, str)
            and self._evaluation_reaches_inferred_closure(self.resolve_ref(node, reference))
        ):
            raise EnforcementUnsupportedError(
                "composition_reference_context",
                "a $ref inside context-sensitive composition or beside validation "
                "siblings reaches a target that inferred closure would modify; add "
                "explicit closure to the target's structured descendants or use the "
                "reference at a pure application site",
                schema_path=_display_path(self.infos[id(node)].path),
            )
        for key, value in node.items():
            child_context = composition_context or key in _CONTEXT_SENSITIVE_REFERENCE_KEYWORDS
            if key in _DEFINITION_KEYWORDS:
                child_context = False
            if key in _NAME_MAP_KEYWORDS and isinstance(value, dict):
                for child in value.values():
                    self._check_context_sensitive_references(child, child_context)
            elif key in _SCHEMA_LIST_KEYWORDS and isinstance(value, list):
                for child in value:
                    self._check_context_sensitive_references(child, child_context)
            elif key in _SCHEMA_KEYWORDS:
                self._check_context_sensitive_references(value, child_context)

    def check_post_transform_safety(
        self,
        root: dict[str, Any],
        resources: Mapping[str, dict[str, Any]],
    ) -> None:
        """Reject co-evaluator and reference contexts changed by inferred closure."""
        for node in self.nodes.values():
            self._check_child_evaluator_overlaps(node)
        self._check_context_sensitive_references(root)
        for resource in resources.values():
            self._check_context_sensitive_references(resource)

    def transform(self, node: Any, context: _FragmentContext = None) -> Any:
        if not isinstance(node, dict):
            return node
        info = self.infos[id(node)]
        out: dict[str, Any] = {}
        for key, value in node.items():
            child_context = _child_fragment_context(context, key)
            if key in _NAME_MAP_KEYWORDS and isinstance(value, dict):
                if key in _DEFINITION_KEYWORDS:
                    child_context = None
                out[key] = {
                    name: self.transform(child, child_context) for name, child in value.items()
                }
            elif key in _SCHEMA_LIST_KEYWORDS and isinstance(value, list):
                out[key] = [self.transform(child, child_context) for child in value]
            elif key in _SCHEMA_KEYWORDS:
                out[key] = self.transform(value, child_context)
            else:
                out[key] = value

        explicit = _has_explicit_closure(out)
        declares = self.declares_properties(node)
        if context == "nested_instance" and declares and not explicit:
            raise EnforcementUnsupportedError(
                "nested_instance_composition",
                "the enforced profile cannot safely infer closure for a nested instance "
                "inside in-place composition; add explicit closure at that object",
                schema_path=_display_path(info.path),
            )
        if context is None and info.embedded_direct_resource and declares and not explicit:
            raise EnforcementUnsupportedError(
                "embedded_resource_context",
                "a structured embedded $id resource is applied directly and reused; "
                "add explicit closure or move it to $defs",
                schema_path=_display_path(info.path),
            )
        if (
            context is None
            and declares
            and not explicit
            and not self._condition_matchers_are_covered(node)
        ):
            raise EnforcementUnsupportedError(
                "conditional_annotation_scope",
                "condition-matcher properties must also be unconditionally evaluated at "
                "the closure site",
                schema_path=_display_path(info.path),
            )
        if context is not None or info.reusable_root or explicit or not declares:
            return out

        needs_annotations = "$ref" in node or any(
            key in _ANNOTATING_IN_PLACE_KEYWORDS for key in node
        )
        self.inferred_closures.add(id(node))
        out["unevaluatedProperties" if needs_annotations else "additionalProperties"] = False
        return out


def _has_explicit_closure(node: Any) -> bool:
    return isinstance(node, dict) and any(key in node for key in _EXPLICIT_CLOSURE_KEYWORDS)


def _child_fragment_context(context: _FragmentContext, keyword: str) -> _FragmentContext:
    if keyword in _DEFINITION_KEYWORDS:
        return None
    if keyword == "contains":
        return "same_instance"
    if (
        keyword in _IN_PLACE_MAP_KEYWORDS
        or keyword in _IN_PLACE_LIST_KEYWORDS
        or keyword in _IN_PLACE_SINGLE_KEYWORDS
    ):
        return "same_instance" if context is None else context
    return "nested_instance" if context is not None else None


def prepare_schema_graph(
    root: dict[str, Any],
    resources: Mapping[str, dict[str, Any]] | None = None,
) -> PreparedSchemaGraph:
    """Apply the checked enforced profile to an offline root/resource graph."""
    supplied = resources or {}
    graph = _SchemaGraph(root, supplied)
    transformed_root = graph.transform(root)
    transformed_resources = {key: graph.transform(resource) for key, resource in supplied.items()}
    graph.check_post_transform_safety(root, supplied)
    assert isinstance(transformed_root, dict)
    assert all(isinstance(resource, dict) for resource in transformed_resources.values())
    return PreparedSchemaGraph(root=transformed_root, resources=transformed_resources)


def apply_enforced_extras(schema: dict[str, Any]) -> dict[str, Any]:
    """Apply the checked enforced profile to one self-contained schema resource."""
    return prepare_schema_graph(schema).root
