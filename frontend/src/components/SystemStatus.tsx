import { useApiStatus } from "../hooks/useApiStatus";

export function SystemStatus() {
  const status = useApiStatus();

  return (
    <section className={`status-panel status-${status.state}`} aria-labelledby="status-title">
      <div className="status-heading">
        <div>
          <p className="eyebrow">Runtime check</p>
          <h2 id="status-title">System readiness</h2>
        </div>
        <span className="status-badge" role="status" aria-live="polite">
          {status.state === "loading" ? "Checking" : status.state === "ready" ? "Ready" : "Unavailable"}
        </span>
      </div>

      <div className="status-body" aria-busy={status.state === "loading"}>
        {status.state === "loading" ? (
          <div className="loading-row">
            <span className="spinner" aria-hidden="true" />
            <p>{status.message}</p>
          </div>
        ) : null}

        {status.state === "ready" ? (
          <dl className="status-grid">
            <div>
              <dt>Backend</dt>
              <dd>{status.data.health.status} · v{status.data.health.version}</dd>
            </div>
            <div>
              <dt>Database</dt>
              <dd>{status.data.readiness.database}</dd>
            </div>
            <div>
              <dt>Environment</dt>
              <dd>{status.data.health.environment}</dd>
            </div>
          </dl>
        ) : null}

        {status.state === "error" ? (
          <div className="error-row" role="alert">
            <div>
              <strong>Readiness check failed</strong>
              <p>{status.message}</p>
            </div>
            <button type="button" className="secondary-button" onClick={status.retry}>
              Retry check
            </button>
          </div>
        ) : null}
      </div>
    </section>
  );
}

