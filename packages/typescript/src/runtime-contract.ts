/** Node.js/Bun runtime binding between a portable contract descriptor and Zod. */
import { z } from "zod";
import { type ContractDescriptor, defineContractDescriptor } from "./models.js";

/**
 * A validated runtime contract. Construct with `bindContract` so the descriptor's
 * serializable model label and its executable Zod binding cannot drift apart.
 */
export class RuntimeContract {
  readonly descriptor: ContractDescriptor;
  readonly semanticModel: z.ZodType | null;

  constructor(descriptor: ContractDescriptor, semanticModel: z.ZodType | null = null) {
    const portable = defineContractDescriptor(descriptor);
    if (portable.model !== null && semanticModel === null) {
      throw new TypeError("contract descriptor names a model but no semantic model was provided");
    }
    if (portable.model === null && semanticModel !== null) {
      throw new TypeError(
        "contract descriptor has no model name but a semantic model was provided",
      );
    }
    if (semanticModel !== null && !(semanticModel instanceof z.ZodType)) {
      throw new TypeError("semantic model must be a Zod schema");
    }
    this.descriptor = portable;
    this.semanticModel = semanticModel;
    Object.freeze(this);
  }
}

/** Bind a portable descriptor to its optional runtime Zod schema exactly once. */
export function bindContract(
  descriptor: ContractDescriptor,
  semanticModel: z.ZodType | null = null,
): RuntimeContract {
  return new RuntimeContract(descriptor, semanticModel);
}
