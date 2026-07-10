import { expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { isFileSystemError } from "../src/node-errors.js";

test("coded non-filesystem errors are not classified as input I/O", () => {
  const parserError = Object.assign(new Error("invalid YAML"), { code: "UNEXPECTED_TOKEN" });

  expect(isFileSystemError(parserError)).toBe(false);
});

test("Node filesystem errors retain input I/O classification", () => {
  const missing = resolve(import.meta.dir, ".definitely-missing-input.yaml");
  let caught: unknown;
  try {
    readFileSync(missing);
  } catch (error) {
    caught = error;
  }

  expect(isFileSystemError(caught)).toBe(true);
});

test("descriptor-based filesystem errors do not need a path property", () => {
  const descriptorError = Object.assign(new Error("is a directory"), {
    code: "EISDIR",
    errno: -21,
    fd: 42,
    syscall: "read",
  });

  expect(isFileSystemError(descriptorError)).toBe(true);
});
