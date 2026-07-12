"""In-memory collection of registered contracts."""

from __future__ import annotations

from softschema.models import Contract, _check_contract_id


class Contracts:
    """Resolve registered contracts by their public id."""

    def __init__(self) -> None:
        self._contracts: dict[str, Contract] = {}

    def register(self, contract: Contract) -> None:
        existing = self._contracts.get(contract.id)
        if existing is not None and existing != contract:
            msg = f"contract {contract.id!r} is already registered"
            raise ValueError(msg)
        self._contracts[contract.id] = contract

    def resolve(self, contract_id: str) -> Contract | None:
        _check_contract_id(contract_id)
        return self._contracts.get(contract_id)

    @property
    def all(self) -> dict[str, Contract]:
        return dict(self._contracts)
