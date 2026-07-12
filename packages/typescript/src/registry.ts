/**
 * In-memory collection that resolves contracts by id: the idiomatic mirror of the
 * Python `Contracts`. Registering a different contract under an existing id is an error.
 */
import { type Contract, checkContractId } from "./models.js";

function contractsEqual(a: Contract, b: Contract): boolean {
  return (
    a.id === b.id &&
    a.model === b.model &&
    a.envelopeKey === b.envelopeKey &&
    a.status === b.status &&
    a.profile === b.profile &&
    a.schemaPath === b.schemaPath
  );
}

export class Contracts {
  private readonly contracts = new Map<string, Contract>();

  register(contract: Contract): void {
    checkContractId(contract.id);
    const existing = this.contracts.get(contract.id);
    if (existing !== undefined && !contractsEqual(existing, contract)) {
      throw new Error(`contract ${JSON.stringify(contract.id)} is already registered`);
    }
    this.contracts.set(contract.id, contract);
  }

  resolve(contractId: string): Contract | null {
    checkContractId(contractId);
    return this.contracts.get(contractId) ?? null;
  }

  get all(): Record<string, Contract> {
    return Object.fromEntries(this.contracts);
  }
}
