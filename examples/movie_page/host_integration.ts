/** Example Node.js/Bun host integration for validating movie page artifacts. */

import { defineContractDescriptor } from "softschema/core";
import {
  type ArtifactValidationResult,
  bindContract,
  validateArtifact,
} from "softschema/node";
import { fileURLToPath } from "node:url";
import { MoviePage } from "./model.js";

export const MOVIE_PAGE_CONTRACT_ID = "example.movies:MoviePage/v1";

const descriptor = defineContractDescriptor({
  id: MOVIE_PAGE_CONTRACT_ID,
  model: "./model.js:MoviePage",
  envelopeKey: "movie",
  status: "enforced",
  profile: "frontmatter-md",
  schemaPath: fileURLToPath(new URL("./movie-page.schema.yaml", import.meta.url)),
});

export const moviePageContract = bindContract(descriptor, MoviePage);

export function validateMoviePage(path: string): ArtifactValidationResult {
  return validateArtifact(path, moviePageContract);
}
