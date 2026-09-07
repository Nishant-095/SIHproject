import { api } from "../api";
import { DataState } from "../components/DataState";
import { LinePlot } from "../components/LinePlot";
import { PageIntro } from "../components/PageIntro";
import { formatAdvanceWindow, formatDate, formatDateTime, formatNumber, percentChange } from "../format";
import { useRemoteData } from "../hooks/useRemoteData";

const changeLabel = (value: number | null) => value === null ? "Not enough history" : `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;
const warningLabel = (value: string) => value.toLowerCase().replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
const periodChange = (rows: { index_value: string | null }[]) => {
  const current = rows.at(-1)?.index_value ?? null;
  const previous = rows.at(-2)?.index_value ?? null;
  return percentChange(current, previous);
};

export function OverviewPage() {
  const result = useRemoteData(async (signal) => {
    const [current, history, coverage, weekly, monthly] = await Promise.all([
      api.currentIndex(signal),
      api.indexHistory(signal),
      api.currentIndexCoverage(signal),
      api.weeklyIndex(signal),
      api.monthlyIndex(signal),
    ]);
    return { current, history, coverage, weekly, monthly };
  });
  const current = result.data?.current;
  const history = result.data?.history ?? [];
  const coverage = result.data?.coverage;
  const weekly = result.data?.weekly ?? [];
  const monthly = result.data?.monthly ?? [];
  const currentValue = current?.index_value ?? null;
  const previous = (days: number) => history.at(-(days + 1))?.index_value ?? null;
  const periodRows = [weekly.at(-1), monthly.at(-1)].filter((row) => row !== undefined);

  return (
    <>
      <PageIntro eyebrow="National fare index" title="Airfare movement, with the evidence attached">
        <p>APIx summarises the fixed India route-and-lead-time basket. Every value below comes from the public API and retains its data class.</p>
      </PageIntro>
      <DataState state={result.state} error={result.error} retry={result.retry}>
        {current ? (
          <>
            <section className="index-banner" aria-labelledby="current-index-title">
              <div><span id="current-index-title">Current APIx</span><strong>{formatNumber(current.index_value, 2)}</strong></div>
              <dl className="metric-line">
                <div><dt>Daily</dt><dd>{changeLabel(percentChange(currentValue, previous(1)))}</dd></div>
                <div><dt>Weekly</dt><dd>{changeLabel(periodChange(weekly))}</dd></div>
                <div><dt>Monthly</dt><dd>{changeLabel(periodChange(monthly))}</dd></div>
                <div><dt>Coverage</dt><dd>{formatNumber(current.coverage_percent)}%</dd></div>
              </dl>
              <div className="index-meta"><span className={`data-badge data-${current.data_class.toLowerCase()}`}>{current.data_class}</span><span>{current.publication_status}</span><span>Updated {formatDateTime(current.calculated_at)} IST</span></div>
            </section>

            {coverage ? (
              <section className={`coverage-advisory confidence-${coverage.confidence_level.toLowerCase()}`} aria-labelledby="confidence-title">
                <div>
                  <h2 id="confidence-title">Coverage confidence: {coverage.confidence_level}</h2>
                  <p>{coverage.source_count} source{coverage.source_count === 1 ? "" : "s"} contributed to this index. No missing value is imputed.</p>
                </div>
                <ul aria-label="Coverage warnings">
                  {coverage.warnings.length ? coverage.warnings.map((warning) => <li key={warning}>{warningLabel(warning)}</li>) : <li>No coverage warnings</li>}
                </ul>
              </section>
            ) : null}

            <div className="dashboard-grid">
              <section className="data-panel span-two" aria-labelledby="history-title">
                <div className="section-heading"><div><h2 id="history-title">Index history</h2><p>Published APIx values by methodological date</p></div><a href="http://localhost:8000/api/v1/exports/index.csv">Download CSV</a></div>
                <LinePlot points={history.map((point) => ({ label: formatDate(point.methodological_date), value: point.index_value === null ? null : Number(point.index_value) }))} label="APIx history" valueLabel="Index" formatValue={(value) => value.toFixed(2)} />
              </section>

              <section className="data-panel" aria-labelledby="coverage-title">
                <h2 id="coverage-title">Basket coverage</h2>
                <div className="coverage-number"><strong>{formatNumber(current.coverage_percent)}%</strong><span>{current.components.filter((item) => item.current_price !== null).length} of {current.components.length} basket cells available</span></div>
                <p className="support-copy">Publication status: <strong>{current.publication_status}</strong>. Missing cells are never silently treated as zero fare.</p>
              </section>

              <section className="data-panel span-three" aria-labelledby="aggregation-title">
                <div className="section-heading"><div><h2 id="aggregation-title">Weekly and monthly aggregation</h2><p>Only published daily APIx values are averaged; incomplete periods remain labelled.</p></div><span className="version-label">No imputation</span></div>
                <div className="table-scroll"><table className="data-table"><thead><tr><th>Period</th><th>APIx</th><th>Status</th><th>Days used</th><th>Average / minimum coverage</th><th>Sources</th><th>Confidence</th><th>Warnings</th></tr></thead><tbody>
                  {periodRows.map((row) => <tr key={row.id}><th>{row.period_type}<small>{formatDate(row.period_start)} – {formatDate(row.period_end)}</small></th><td>{formatNumber(row.index_value, 2)}</td><td>{warningLabel(row.aggregation_status)}</td><td>{row.valued_day_count} / {row.expected_day_count}</td><td>{formatNumber(row.average_coverage_percent)}% / {formatNumber(row.minimum_coverage_percent)}%</td><td>{row.source_count}</td><td><span className={`confidence-label confidence-${row.confidence_level.toLowerCase()}`}>{row.confidence_level}</span></td><td>{row.warnings.length ? row.warnings.map(warningLabel).join(", ") : "None"}</td></tr>)}
                  {!periodRows.length ? <tr><td colSpan={8}>No weekly or monthly aggregate has been calculated yet.</td></tr> : null}
                </tbody></table></div>
              </section>

              {coverage ? (
                <section className="data-panel span-three" aria-labelledby="route-coverage-title">
                  <div className="section-heading"><div><h2 id="route-coverage-title">Route coverage and source dispersion</h2><p>Coverage is shown route by route, including missing windows and source concentration.</p></div><span className="version-label">Threshold {formatNumber(coverage.missing_data_policy.minimum_publication_coverage_percent)}%</span></div>
                  <div className="dispersion-line" aria-label="Source dispersion">{coverage.source_dispersion.length ? coverage.source_dispersion.map((source) => <span key={source.source_code}><strong>{source.source_code}</strong> {formatNumber(source.share_percent)}% ({source.observation_count})</span>) : <span>No contributing observations</span>}</div>
                  <div className="table-scroll"><table className="data-table"><thead><tr><th>Route</th><th>Windows</th><th>Coverage</th><th>Sources</th><th>Observations</th><th>Confidence</th><th>Missing windows</th></tr></thead><tbody>
                    {coverage.routes.map((route) => <tr key={`${route.origin_iata}-${route.destination_iata}`}><th>{route.origin_iata}–{route.destination_iata}</th><td>{route.available_windows} / {route.total_windows}</td><td>{formatNumber(route.coverage_percent)}%</td><td>{route.source_count}</td><td>{route.observation_count}</td><td><span className={`confidence-label confidence-${route.confidence_level.toLowerCase()}`}>{route.confidence_level}</span></td><td>{route.missing_windows.length ? route.missing_windows.map(formatAdvanceWindow).join(", ") : "None"}</td></tr>)}
                  </tbody></table></div>
                </section>
              ) : null}

              <section className="data-panel span-three" aria-labelledby="heatmap-title">
                <div className="section-heading"><div><h2 id="heatmap-title">Route and advance-window matrix</h2><p>Price relative by fixed basket cell; 100 equals its base fare.</p></div><span className="version-label">Basket {current.basket_version}</span></div>
                <div className="table-scroll"><table className="data-table heat-table"><thead><tr><th>Route</th>{["T1", "T7", "T15", "T30", "T45"].map((window) => <th key={window}>{formatAdvanceWindow(window)}</th>)}</tr></thead><tbody>
                  {[...new Set(current.components.map((item) => `${item.origin_iata}-${item.destination_iata}`))].map((route) => <tr key={route}><th>{route}</th>{["T1", "T7", "T15", "T30", "T45"].map((window) => {
                    const cell = current.components.find((item) => `${item.origin_iata}-${item.destination_iata}` === route && item.advance_window === window);
                    const relative = cell?.price_relative === null || cell?.price_relative === undefined ? null : Number(cell.price_relative);
                    return <td key={window}><span className={relative === null ? "heat-cell missing" : relative > 105 ? "heat-cell high" : relative < 95 ? "heat-cell low" : "heat-cell steady"}>{relative === null ? "Missing" : relative.toFixed(1)}</span></td>;
                  })}</tr>)}
                </tbody></table></div>
              </section>
            </div>
          </>
        ) : null}
      </DataState>
    </>
  );
}
