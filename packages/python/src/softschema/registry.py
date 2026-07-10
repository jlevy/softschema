"""In-memory collection of registered contracts."""

from __future__ import annotations

from softschema.models import Contract, validate_contract_id


class Contracts:
    """Resolve registered contracts by their public id."""

    def __init__(self) -> None:
        self._contracts: dict[str, Contract] = {}

    def register(self, contract: Contract) -> None:
        contract_id = validate_contract_id(contract.id)
        existing = self._contracts.get(contract_id)
        if existing is not None and existing != contract:
            msg = f"contract {contract_id!r} is already registered"
            raise ValueError(msg)
        self._contracts[contract_id] = contract

    def resolve(self, contract_id: str) -> Contract | None:
        return self._contracts.get(validate_contract_id(contract_id))

    @property
    def all(self) -> dict[str, Contract]:
        return dict(self._contracts)
