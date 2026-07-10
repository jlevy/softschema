import { expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const ROOT = resolve(import.meta.dir, "../../..");
const ADAPTER = resolve(ROOT, "conformance/adapters/javascript-adapter.mjs");
const NODE_ENTRY = resolve(ROOT, "packages/typescript/src/node.ts");
const CORE_ENTRY = resolve(ROOT, "packages/typescript/src/core/index.ts");
const MAX_REQUEST_BYTES = 16 * 1024 * 1024;
const CHILD_OUTPUT_HEADROOM_BYTES = 1024 * 1024;
const INVALID_REQUESTS = JSON.parse(
  readFileSync(resolve(ROOT, "tests/parity/conformance-adapter-invalid-requests.json"), "utf8"),
) as { id: string; request: unknown; message: string }[];

function runAdapter(input: string | Uint8Array) {
  return spawnSync(process.execPath, [ADAPTER, NODE_ENTRY, CORE_ENTRY, NODE_ENTRY], {
    input,
    maxBuffer: MAX_REQUEST_BYTES + CHILD_OUTPUT_HEADROOM_BYTES,
  });
}

test("standalone JavaScript adapter accepts one strict vector request", () => {
  const request = {
    format: "softschema-vector-suite-v1",
    id: "adapter-smoke",
    operation: "identity",
    cases: [
      {
        id: "valid-contract",
        input: { kind: "contract", value: "example:Thing/v1" },
        expected: { ok: true, value: "example:Thing/v1" },
      },
    ],
  };
  const child = runAdapter(JSON.stringify(request));

  expect(child.status).toBe(0);
  expect(child.stderr.toString()).toBe("");
  expect(JSON.parse(child.stdout.toString())).toEqual({
    format: "softschema-vector-results-v1",
    id: "adapter-smoke",
    results: [{ id: "valid-contract", actual: { ok: true, value: "example:Thing/v1" } }],
  });
});

test("standalone JavaScript adapter rejects hostile JSON without a traceback", () => {
  const validTail =
    '"id":"bad","operation":"identity","cases":[' +
    '{"id":"case","input":{},"expected":{}}]}';
  const requests: (string | Uint8Array)[] = [
    `{"format":"softschema-vector-suite-v1","format":"softschema-vector-suite-v1",${validTail}`,
    '{"format":"softschema-vector-suite-v1","id":"bad","operation":"identity",' +
      '"description":"\\ud800","cases":[{"id":"case","input":{},"expected":{}}]}',
    '{"format":"softschema-vector-suite-v1","id":"bad","operation":"identity",' +
      '"cases":[{"id":"case","input":{"value":1e999},"expected":{}}]}',
    `[${"[".repeat(128)}0${"]".repeat(128)}]`,
    new Uint8Array([0xff]),
    new Uint8Array(MAX_REQUEST_BYTES + 1).fill(0x20),
  ];

  for (const input of requests) {
    const child = runAdapter(input);
    expect(child.status).toBe(2);
    expect(child.stdout.toString()).toBe("");
    expect(child.stderr.toString()).toStartWith("softschema vector adapter: ");
    expect(child.stderr.toString()).not.toContain(" at ");
  }
});

test("standalone JavaScript adapter rejects shared invalid requests without a traceback", () => {
  for (const vector of INVALID_REQUESTS) {
    const child = runAdapter(JSON.stringify(vector.request));
    expect(child.status, vector.id).toBe(2);
    expect(child.stdout.toString(), vector.id).toBe("");
    expect(child.stderr.toString(), vector.id).toBe(
      `softschema vector adapter: ${vector.message}\n`,
    );
  }
});

test("standalone JavaScript adapter accepts JSON integer limit spellings", () => {
  const request =
    '{"format":"softschema-vector-suite-v1","id":"limit-integer-spelling",' +
    '"operation":"portable-yaml","cases":[{"id":"one-point-zero",' +
    '"input":{"text":"null","limits":{"max_depth":1.0}},"expected":{}}]}';
  const child = runAdapter(request);

  expect(child.status).toBe(0);
  expect(child.stderr.toString()).toBe("");
  expect(JSON.parse(child.stdout.toString()).results).toEqual([
    { id: "one-point-zero", actual: { ok: true, value: null } },
  ]);
});
