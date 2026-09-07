import { PageIntro } from "../components/PageIntro";

const routes = ["DEL → BOM", "DEL → BLR", "BOM → BLR"];
const windows = ["T+1", "T+7", "T+15", "T+30", "T+45"];

export function ContractPage() {
  return (
    <>
      <PageIntro eyebrow="Frozen project contract" title="A small, comparable fare basket">
        <p>
          One adult, one-way, economy, non-stop, public INR fares observed daily at 10:00
          Asia/Kolkata.
        </p>
      </PageIntro>
      <div className="contract-grid">
        <section className="contract-card" aria-labelledby="route-title">
          <p className="eyebrow">Route basket</p>
          <h2 id="route-title">Three directed routes</h2>
          <ul className="code-list">
            {routes.map((route) => <li key={route}>{route}</li>)}
          </ul>
        </section>
        <section className="contract-card" aria-labelledby="window-title">
          <p className="eyebrow">Booking windows</p>
          <h2 id="window-title">Five fixed lead times</h2>
          <ul className="window-list">
            {windows.map((window) => <li key={window}>{window}</li>)}
          </ul>
        </section>
      </div>
      <aside className="method-note">
        <strong>Methodological boundary</strong>
        <p>
          Real-source approval, canonical cross-source fares, and Prototype APIx calculation are
          later phases. Synthetic evidence is never labelled live.
        </p>
      </aside>
    </>
  );
}

