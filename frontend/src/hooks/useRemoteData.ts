import { useCallback, useEffect, useState } from "react";

type RemoteState<T> =
  | { state: "loading"; data: null; error: null }
  | { state: "ready"; data: T; error: null }
  | { state: "error"; data: null; error: string };

export function useRemoteData<T>(loader: (signal: AbortSignal) => Promise<T>, dependencies: readonly unknown[] = []) {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<RemoteState<T>>({ state: "loading", data: null, error: null });

  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort("Request timed out"), 8_000);
    queueMicrotask(() => {
      if (!controller.signal.aborted) setResult({ state: "loading", data: null, error: null });
    });
    loader(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setResult({ state: "ready", data, error: null });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted && controller.signal.reason !== "Request timed out") return;
        setResult({
          state: "error",
          data: null,
          error: controller.signal.reason === "Request timed out"
            ? "The API request timed out. Confirm the backend is running, then retry."
            : error instanceof Error ? error.message : "The API request failed.",
        });
      })
      .finally(() => window.clearTimeout(timeout));
    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  // Callers pass stable loaders and explicit primitive dependencies.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt, ...dependencies]);

  const retry = useCallback(() => setAttempt((value) => value + 1), []);
  return { ...result, retry };
}
