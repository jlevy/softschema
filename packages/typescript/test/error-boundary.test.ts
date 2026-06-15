/**
 * Regression tests for the CLI's per-command error boundary (ss-gand / ss-6mdz, and the
 * follow-up that the boundary must reach every command handler, not just the top-level
 * guard). A programmer bug (TypeError / RangeError / ReferenceError) thrown from inside
 * any command helper must crash, never be masked as a clean exit 2; every other error is
 * a one-line stderr message + exit 2. These exercise `reportUserError` directly, the
 * single boundary each command's catch now delegates to — the TypeScript parallel of the
 * Python `test_run_cmd_surfaces_internal_bugs` / `test_run_cmd_reports_usage_error_as_exit_2`.
 */
import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { isProgrammerBug, reportUserError } from "../src/cli.js";

describe("isProgrammerBug", () => {
  test("true for bug-indicator exceptions", () => {
    expect(isProgrammerBug(new TypeError("x"))).toBe(true);
    expect(isProgrammerBug(new RangeError("x"))).toBe(true);
    expect(isProgrammerBug(new ReferenceError("x"))).toBe(true);
  });
  test("false for user errors and non-Error throwables", () => {
    expect(isProgrammerBug(new Error("plain user error"))).toBe(false);
    expect(isProgrammerBug(new SyntaxError("malformed input"))).toBe(false);
    expect(isProgrammerBug("string thrown")).toBe(false);
    expect(isProgrammerBug(undefined)).toBe(false);
  });
});

describe("reportUserError (per-command boundary)", () => {
  let chunks: string[] = [];
  let originalWrite: typeof process.stderr.write;
  beforeEach(() => {
    chunks = [];
    originalWrite = process.stderr.write.bind(process.stderr);
    process.stderr.write = ((chunk: string | Uint8Array) => {
      chunks.push(typeof chunk === "string" ? chunk : new TextDecoder().decode(chunk));
      return true;
    }) as typeof process.stderr.write;
  });
  afterEach(() => {
    process.stderr.write = originalWrite;
  });

  test("rethrows bug-indicator exceptions instead of masking them as exit 2", () => {
    // The core regression: a programmer bug thrown from a command helper must surface, so
    // each command's catch (which calls reportUserError) must rethrow it, not return 2.
    expect(() => reportUserError("validate", new TypeError("internal bug"))).toThrow(TypeError);
    expect(() => reportUserError("compile", new RangeError("oob"))).toThrow(RangeError);
    expect(() => reportUserError("generate: a.md", new ReferenceError("x"))).toThrow(
      ReferenceError,
    );
    expect(chunks.join("")).toBe(""); // a crash writes nothing to the boundary's stderr
  });

  test("reports a user error as a clean one-line message + exit 2", () => {
    const code = reportUserError("validate", new Error("bad flag"));
    expect(code).toBe(2);
    expect(chunks.join("")).toBe("softschema validate: bad flag\n");
  });

  test("preserves each command's message prefix (e.g. generate keeps the path)", () => {
    expect(reportUserError("generate: docs/x.md", new Error("missing marker"))).toBe(2);
    expect(chunks.join("")).toBe("softschema generate: docs/x.md: missing marker\n");
  });
});
