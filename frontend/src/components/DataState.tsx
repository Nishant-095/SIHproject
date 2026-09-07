import type { ReactNode } from "react";

type Props = {
  state: "loading" | "ready" | "error";
  error: string | null;
  retry: () => void;
  empty?: boolean;
  emptyMessage?: string;
  children: ReactNode;
};

export function DataState({ state, error, retry, empty = false, emptyMessage = "No matching data is available yet.", children }: Props) {
  if (state === "loading") {
    return <div className="data-state" aria-busy="true"><span className="spinner" aria-hidden="true" /><p>Loading verified API data</p></div>;
  }
  if (state === "error") {
    return (
      <div className="data-state error-state" role="alert">
        <div><strong>Data could not be loaded</strong><p>{error}</p></div>
        <button className="secondary-button" type="button" onClick={retry}>Retry</button>
      </div>
    );
  }
  if (empty) return <div className="data-state empty-state"><p>{emptyMessage}</p></div>;
  return <>{children}</>;
}
