/**
 * Single source of truth for the repo files bundled into the npm package's
 * `resources/` directory (the TypeScript analogue of the Python wheel
 * `force-include` map). `copy-resources.ts` copies these at build time and the
 * resource-manifest test asserts every CLI `DOC_TOPICS` path is covered here, so
 * a topic can never reference a file that is not shipped.
 *
 * Keep in sync with the wheel `force-include` map in the root `pyproject.toml`.
 */
export const RESOURCE_PATHS: readonly string[] = [
  "README.md",
  "docs/softschema-guide.md",
  "docs/softschema-spec.md",
  "docs/softschema-python-design.md",
  "docs/softschema-typescript-design.md",
  "docs/development.md",
  "docs/installation.md",
  "examples/movie_page/README.md",
  "examples/movie_page/spirited-away.md",
  "examples/movie_page/model.py",
  "examples/movie_page/host_integration.py",
  "examples/movie_page/movie-page.schema.yaml",
  "skills/softschema/SKILL.md",
];
