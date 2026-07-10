/** Node filesystem failures include numeric errno and syscall context, unlike parser codes. */
export function isFileSystemError(
  error: unknown,
): error is NodeJS.ErrnoException & { code: string; errno: number; syscall: string } {
  if (!(error instanceof Error)) return false;
  const candidate = error as NodeJS.ErrnoException;
  return (
    typeof candidate.code === "string" &&
    typeof candidate.errno === "number" &&
    typeof candidate.syscall === "string" &&
    candidate.syscall.length > 0
  );
}
