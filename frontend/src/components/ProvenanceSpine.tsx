const stages = [
  { label: "Fixture source", detail: "Deterministic and clearly synthetic", state: "complete" },
  { label: "Raw evidence", detail: "Hashed, source-shaped and retained", state: "complete" },
  { label: "Normalized fare", detail: "Quality decision remains traceable", state: "complete" },
  { label: "Prototype APIx", detail: "Deliberately scheduled for Phase 6", state: "future" },
] as const;

export function ProvenanceSpine() {
  return (
    <section className="spine-card" aria-labelledby="spine-title">
      <p className="eyebrow">Implemented path</p>
      <h2 id="spine-title">Evidence before index</h2>
      <ol className="provenance-spine">
        {stages.map((stage) => (
          <li key={stage.label} className={stage.state}>
            <span className="spine-marker" aria-hidden="true" />
            <div>
              <strong>{stage.label}</strong>
              <span>{stage.detail}</span>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

