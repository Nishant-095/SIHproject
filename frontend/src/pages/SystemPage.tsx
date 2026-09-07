import { PageIntro } from "../components/PageIntro";
import { ProvenanceSpine } from "../components/ProvenanceSpine";
import { SystemStatus } from "../components/SystemStatus";

export function SystemPage() {
  return (
    <>
      <PageIntro eyebrow="Foundation console · Phase 1–3" title="Prove the pipeline before the index">
        <p>
          This screen reports infrastructure truth. It does not display fabricated live fares or a
          placeholder APIx.
        </p>
      </PageIntro>
      <div className="content-grid">
        <SystemStatus />
        <ProvenanceSpine />
      </div>
      <section className="scope-strip" aria-label="Current implementation scope">
        <div><span>Routes</span><strong>3 frozen</strong></div>
        <div><span>Windows</span><strong>T+1 to T+45</strong></div>
        <div><span>Collection</span><strong>Fixture only</strong></div>
        <div><span>Data class</span><strong>SYNTHETIC</strong></div>
      </section>
    </>
  );
}

