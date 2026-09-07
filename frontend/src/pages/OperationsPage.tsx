import { api } from "../api";
import { DataState } from "../components/DataState";
import { LinePlot } from "../components/LinePlot";
import { PageIntro } from "../components/PageIntro";
import { formatAdvanceWindow, formatDate, formatDateTime, formatNumber } from "../format";
import { useRemoteData } from "../hooks/useRemoteData";

const alertStates = new Set(["DEGRADED", "BLOCKED", "PARSER_CHANGED"]);

export function OperationsPage() {
  const summary = useRemoteData(async (signal) => {
    const [runs, sources, healthHistory, quality] = await Promise.all([api.runs(signal), api.sourceHealth(signal), api.sourceHealthHistory(signal), api.quality(signal)]);
    return { runs, sources, healthHistory, quality };
  });
  const latestId = summary.data?.runs[0]?.id ?? "";
  const runDetail = useRemoteData((signal) => latestId ? api.run(latestId, signal) : Promise.resolve(null), [latestId]);
  const alerts = summary.data?.sources.filter((source) => alertStates.has(source.health_status)) ?? [];

  return (
    <>
      <PageIntro eyebrow="Collection control room" title="Know what ran, what failed, and whether the index is publishable">
        <p>This read-only operations view exposes job outcomes, source health, observation quality, and basket coverage. Administrative controls remain token-protected in the API.</p>
      </PageIntro>
      <DataState state={summary.state} error={summary.error} retry={summary.retry}>
        {summary.data ? <>
          {alerts.length ? <section className="alert-stack" aria-label="Source alerts">{alerts.map((source) => <div role="alert" key={source.source_code}><strong>{source.source_code}: {source.health_status}</strong><span>{source.last_failure_code ?? "The source needs operator attention."}</span></div>)}</section> : <div className="all-clear" role="status">No degraded, blocked, or parser-change source alerts.</div>}
          <section className="ops-strip" aria-label="Operations summary"><div><span>Last run</span><strong>{summary.data.runs[0] ? formatDate(summary.data.runs[0].methodological_date) : "No run"}</strong></div><div><span>Valid observations</span><strong>{summary.data.quality.included_observations}</strong></div><div><span>Quality score</span><strong>{formatNumber(summary.data.quality.average_quality_score, 1)}</strong></div><div><span>Inclusion rate</span><strong>{formatNumber(summary.data.quality.inclusion_rate_percent)}%</strong></div></section>
          <div className="dashboard-grid">
            <section className="data-panel span-three" aria-labelledby="health-trend-title"><div className="section-heading"><div><h2 id="health-trend-title">Collection success history</h2><p>Daily job success rate for the fixture source; source states remain listed below.</p></div></div><LinePlot points={summary.data.healthHistory.filter((point) => point.source_code === "FIXTURE_LOCAL").map((point) => ({ label: formatDate(point.methodological_date), value: point.success_rate }))} label="Fixture source collection success history" valueLabel="Success rate" formatValue={(value) => `${formatNumber(value)}%`} /></section>
            <section className="data-panel span-two" aria-labelledby="jobs-title"><div className="section-heading"><div><h2 id="jobs-title">Latest collection jobs</h2><p>{summary.data.runs[0] ? `${summary.data.runs[0].status} · ${formatDateTime(summary.data.runs[0].finished_at)} IST` : "No collection run has been recorded."}</p></div></div><DataState state={runDetail.state} error={runDetail.error} retry={runDetail.retry} empty={runDetail.data === null}>{runDetail.data ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Window</th><th>Travel date</th><th>Status</th><th>Attempts</th><th>Failure</th></tr></thead><tbody>{runDetail.data.jobs.map((job) => <tr key={job.id}><td>{formatAdvanceWindow(job.advance_window)}</td><td>{formatDate(job.travel_date)}</td><td><span className={`compact-status status-${job.status.toLowerCase()}`}>{job.status}</span></td><td>{job.attempt_count}</td><td>{job.failure_code ?? "—"}</td></tr>)}</tbody></table></div> : null}</DataState></section>
            <section className="data-panel" aria-labelledby="failure-title"><h2 id="failure-title">Quality decisions</h2><ul className="plain-list"><li><span>Included</span><strong>{summary.data.quality.included_observations}</strong></li><li><span>Excluded</span><strong>{summary.data.quality.excluded_observations}</strong></li><li><span>Flagged</span><strong>{summary.data.quality.flagged_observations}</strong></li></ul>{Object.keys(summary.data.quality.flag_counts).length ? <details><summary>Flag breakdown</summary><ul className="plain-list">{Object.entries(summary.data.quality.flag_counts).map(([flag, count]) => <li key={flag}><span>{flag}</span><strong>{count}</strong></li>)}</ul></details> : null}</section>
            <section className="data-panel span-three" aria-labelledby="sources-title"><h2 id="sources-title">Source health</h2><div className="table-scroll"><table className="data-table"><thead><tr><th>Source</th><th>State</th><th>Success rate</th><th>Failures</th><th>Avg latency</th><th>Last success</th><th>Parser</th></tr></thead><tbody>{summary.data.sources.map((source) => <tr key={source.source_code}><td><strong>{source.source_name}</strong><small>{source.source_code} · {source.review_status}</small></td><td><span className={`compact-status health-${source.health_status.toLowerCase()}`}>{source.health_status}</span></td><td>{source.success_rate === null ? "—" : `${formatNumber(source.success_rate)}%`}</td><td>{source.failed_jobs}</td><td>{source.average_duration_ms === null ? "—" : `${source.average_duration_ms} ms`}</td><td>{formatDateTime(source.last_success_at)}</td><td>{source.parser_version}</td></tr>)}</tbody></table></div></section>
            <section className="data-panel span-three" aria-labelledby="runs-title"><h2 id="runs-title">Recent runs</h2><div className="table-scroll"><table className="data-table"><thead><tr><th>Date</th><th>Class</th><th>Status</th><th>Jobs</th><th>Valid observations</th></tr></thead><tbody>{summary.data.runs.map((run) => <tr key={run.id}><td>{formatDate(run.methodological_date)}</td><td><span className={`data-badge data-${run.data_class.toLowerCase()}`}>{run.data_class}</span></td><td>{run.status}</td><td>{run.successful_jobs} success / {run.failed_jobs} failed</td><td>{run.valid_observations}</td></tr>)}</tbody></table></div></section>
          </div>
        </> : null}
      </DataState>
    </>
  );
}
