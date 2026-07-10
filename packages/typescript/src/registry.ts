/**
 * In-memory collection that resolves contracts by id: the idiomatic mirror of the
 * Python `Contracts`. Registering a different contract under an existing id is an error.
 */
import { type Contract, defineContract, validateContractId } from "./models.js";

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
    const stored = defineContract(contract);
    const contractId = stored.id;
    const existing = this.contracts.get(contractId);
    if (existing !== undefined && !contractsEqual(existing, stored)) {
      throw new Error(`contract ${JSON.stringify(contract.id)} is already registered`);
    }
    this.contracts.set(contractId, stored);
  }

  resolve(contractId: string): Contract | null {
    return this.contracts.get(validateContractId(contractId)) ?? null;
  }

  get all(): Record<string, Contract> {
    return Object.fromEntries(this.contracts);
  }
}
