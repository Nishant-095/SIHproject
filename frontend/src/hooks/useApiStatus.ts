import { useCallback, useEffect, useRef, useState } from "react";

import { fetchSystemStatus, type SystemPayload } from "../api";

type ApiStatusState =
  | { state: "loading"; data: null; message: string }
  | { state: "ready"; data: SystemPayload; message: string }
  | { state: "error"; data: null; message: string };

const REQUEST_TIMEOUT_MS = 5_000;

export function useApiStatus() {
  const [attempt, setAttempt] = useState(0);
  const [status, setStatus] = useState<ApiStatusState>({
    state: "loading",
    data: null,
    message: "Checking backend and database readiness",
  });
  const activeRequest = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let timedOut = false;
    activeRequest.current?.abort();
    activeRequest.current = controller;
    const timeout = window.setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, REQUEST_TIMEOUT_MS);

    fetchSystemStatus(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setStatus({ state: "ready", data, message: "Backend and database are ready" });
        }
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted && !timedOut) {
          return;
        }
        setStatus({
          state: "error",
          data: null,
          message: timedOut
            ? "The readiness check timed out. Confirm the backend is running."
            : error instanceof Error
              ? error.message
              : "The readiness check failed.",
        });
      })
      .finally(() => window.clearTimeout(timeout));

    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [attempt]);

  const retry = useCallback(() => {
    setStatus({
      state: "loading",
      data: null,
      message: "Checking backend and database readiness",
    });
    setAttempt((value) => value + 1);
  }, []);

  return { ...status, retry };
}
