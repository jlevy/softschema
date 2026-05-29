"""In-memory registry for schema bindings."""

from __future__ import annotations

from softschema.models import SoftschemaBinding


class SoftschemaRegistry:
    """Resolve complete bindings by public contract ID."""

    def __init__(self) -> None:
        self._bindings: dict[str, SoftschemaBinding] = {}

    def register(self, binding: SoftschemaBinding) -> None:
        existing = self._bindings.get(binding.contract_id)
        if existing is not None and existing != binding:
            msg = f"contract {binding.contract_id!r} is already registered"
            raise ValueError(msg)
        self._bindings[binding.contract_id] = binding

    def resolve(self, contract_id: str) -> SoftschemaBinding | None:
        return self._bindings.get(contract_id)

    @property
    def bindings(self) -> dict[str, SoftschemaBinding]:
        return dict(self._bindings)
