import { readFileSync } from "node:fs";
import { parse as parseYaml } from "yaml";

export function loadYamlFixture<T>(path: string): T {
  return parseYaml(readFileSync(path, "utf8")) as T;
}
