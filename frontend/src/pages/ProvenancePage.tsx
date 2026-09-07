import { useState } from "react";

import { api } from "../api";
import { DataState } from "../components/DataState";
import { PageIntro } from "../components/PageIntro";
import { formatAdvanceWindow, formatCurrency, formatDate, formatDateTime, formatNumber } from "../format";
import { useRemoteData } from "../hooks/useRemoteData";

export function ProvenancePage() {
  const observations = useRemoteData(api.observations);
  const [selected, setSelected] = useState("");
  const effectiveId = selected || observations.data?.[0]?.id || "";
  const provenance = useRemoteData((signal) => effectiveId ? api.provenance(effectiveId, signal) : Promise.resolve(null), [effectiveId]);

  return (
    <>
      <PageIntro eyebrow="Observation audit" title="Follow a fare from source evidence to index eligibility">
        <p>Select any observation to inspect the original query, raw payload, normalized fields, quality decision, and collection identifiers.</p>
      </PageIntro>
      <div className="provenance-layout">
        <section className="observation-list" aria-labelledby="observation-list-title">
          <div className="list-heading"><h2 id="observation-list-title">Recent observations</h2><a href="http://localhost:8000/api/v1/exports/fare-observations.csv">CSV</a></div>
          <DataState state={observations.state} error={observations.error} retry={observations.retry} empty={observations.data?.length === 0}>
          <ul>{observations.data?.map((item) => <li key={item.id}><button type="button" className={effectiveId === item.id ? "observation-button selected" : "observation-button"} onClick={() => setSelected(item.id)} aria-pressed={effectiveId === item.id}><span><strong>{item.origin_iata}–{item.destination_iata}</strong><small>{item.carrier_code ?? "Unknown"} {item.flight_number ?? ""} · {formatAdvanceWindow(item.advance_window)}</small></span><span><strong>{formatCurrency(item.total_fare)}</strong><small>{formatDate(item.travel_date)}</small></span></button></li>)}</ul>
          </DataState>
        </section>
        <section className="provenance-detail" aria-live="polite">
          <DataState state={provenance.state} error={provenance.error} retry={provenance.retry} empty={provenance.data === null}>
            {provenance.data ? <>
              <div className="audit-header"><div><span className="data-badge data-synthetic">{provenance.data.raw_quote.data_class}</span><h2>{provenance.data.route} · {formatAdvanceWindow(provenance.data.observation.advance_window)}</h2><p>{provenance.data.source_name} · observed {formatDateTime(provenance.data.observation.observed_at_utc)} IST</p></div><span className={provenance.data.observation.included_in_index ? "decision included" : "decision excluded"}>{provenance.data.observation.included_in_index ? "Included in index" : "Excluded"}</span></div>
              <ol className="audit-spine">
                <li><span className="audit-marker" /><div><h3>Source and collection</h3><dl className="detail-grid"><div><dt>Source</dt><dd>{provenance.data.source_code}</dd></div><div><dt>Collection run</dt><dd>{provenance.data.collection_run_id}</dd></div><div><dt>Collection job</dt><dd>{provenance.data.collection_job_id}</dd></div><div><dt>Parser</dt><dd>{provenance.data.raw_quote.parser_version}</dd></div></dl></div></li>
                <li><span className="audit-marker" /><div><h3>Raw quote</h3><dl className="detail-grid"><div><dt>Query</dt><dd>{provenance.data.raw_quote.query_origin}–{provenance.data.raw_quote.query_destination}, {formatDate(provenance.data.raw_quote.query_travel_date)}</dd></div><div><dt>Fare text</dt><dd>{provenance.data.raw_quote.raw_fare_text ?? "Not supplied"}</dd></div><div><dt>Raw total</dt><dd>{formatCurrency(provenance.data.raw_quote.raw_total_fare)}</dd></div><div><dt>Content hash</dt><dd>{provenance.data.raw_quote.content_hash}</dd></div></dl><details><summary>View preserved raw payload</summary><pre>{JSON.stringify(provenance.data.raw_quote.raw_payload, null, 2)}</pre></details></div></li>
                <li><span className="audit-marker" /><div><h3>Normalized fare</h3><dl className="detail-grid"><div><dt>Flight identity</dt><dd>{provenance.data.observation.flight_identity ?? "Not available"}</dd></div><div><dt>Carrier</dt><dd>{provenance.data.observation.carrier_name ?? provenance.data.observation.carrier_code ?? "Not available"}</dd></div><div><dt>Base fare</dt><dd>{formatCurrency(provenance.data.observation.base_fare)}</dd></div><div><dt>Taxes</dt><dd>{formatCurrency(provenance.data.observation.taxes)}</dd></div><div><dt>Other fees</dt><dd>{formatCurrency(provenance.data.observation.other_fees)}</dd></div><div><dt>Total fare</dt><dd>{formatCurrency(provenance.data.observation.total_fare)}</dd></div></dl></div></li>
                <li><span className="audit-marker" /><div><h3>Quality and eligibility</h3><dl className="detail-grid"><div><dt>Quality status</dt><dd>{provenance.data.observation.quality_status}</dd></div><div><dt>Quality score</dt><dd>{formatNumber(provenance.data.observation.quality_score, 0)}</dd></div><div><dt>Flags</dt><dd>{provenance.data.observation.quality_flags.length ? provenance.data.observation.quality_flags.join(", ") : "None"}</dd></div><div><dt>Normalization</dt><dd>{provenance.data.observation.normalization_version}</dd></div><div><dt>Decision reason</dt><dd>{provenance.data.observation.exclusion_reason ?? "Passed inclusion rules"}</dd></div></dl></div></li>
              </ol>
            </> : null}
          </DataState>
        </section>
      </div>
    </>
  );
}
