import { useState } from "react";

import { api } from "../api";
import { DataState } from "../components/DataState";
import { LinePlot } from "../components/LinePlot";
import { PageIntro } from "../components/PageIntro";
import { formatAdvanceWindow, formatCurrency, formatDate, formatNumber } from "../format";
import { useRemoteData } from "../hooks/useRemoteData";

export function RouteExplorerPage() {
  const routesResult = useRemoteData(api.routes);
  const [selection, setSelection] = useState<string>("");
  const effective = selection || (routesResult.data?.[0] ? `${routesResult.data[0].origin_iata}-${routesResult.data[0].destination_iata}` : "");
  const [origin, destination] = effective.split("-");
  const detail = useRemoteData(async (signal) => {
    if (!origin || !destination) return null;
    const [route, history, leadTime] = await Promise.all([
      api.route(origin, destination, signal), api.routeHistory(origin, destination, signal), api.leadTime(origin, destination, signal),
    ]);
    return { route, history, leadTime };
  }, [origin, destination]);

  return (
    <>
      <PageIntro eyebrow="Fixed basket explorer" title="Inspect one route across five booking windows">
        <p>Compare route index, median fares, participating carriers, coverage, and the observed lead-time curve without leaving the public API.</p>
      </PageIntro>
      <DataState state={routesResult.state} error={routesResult.error} retry={routesResult.retry} empty={routesResult.data?.length === 0}>
        <div className="toolbar">
          <span className="toolbar-label">Route board</span>
          <div className="route-switch" role="group" aria-label="Select a fixed-basket route">
            {routesResult.data?.map((route) => {
              const code = `${route.origin_iata}-${route.destination_iata}`;
              return <button type="button" key={route.id} aria-pressed={effective === code} onClick={() => setSelection(code)}><span>{route.origin_iata}</span><i aria-hidden="true" /><span>{route.destination_iata}</span></button>;
            })}
          </div>
          <label className="route-select-label" htmlFor="route-select">Route</label>
          <select id="route-select" className="route-select-native" value={effective} onChange={(event) => setSelection(event.target.value)}>{routesResult.data?.map((route) => { const code = `${route.origin_iata}-${route.destination_iata}`; return <option key={route.id} value={code}>{code}</option>; })}</select>
          <span className="data-badge data-synthetic">SYNTHETIC</span>
        </div>
      </DataState>
      {effective ? <DataState state={detail.state} error={detail.error} retry={detail.retry} empty={detail.data === null}>
        {detail.data ? <div className="dashboard-grid route-dashboard">
          <section className="route-dispatch span-three"><div><span>Selected route</span><strong>{effective}</strong></div><dl><div><dt>Current route index</dt><dd>{formatNumber(detail.data.route.latest_route_index, 2)}</dd></div><div><dt>Latest date</dt><dd>{formatDate(detail.data.route.latest_date)}</dd></div><div><dt>Carriers observed</dt><dd>{detail.data.route.carriers.length ? detail.data.route.carriers.join(", ") : "None yet"}</dd></div></dl></section>
          <section className="data-panel span-two" aria-labelledby="route-history-title"><h2 id="route-history-title">Fare history</h2><p className="support-copy">Average eligible fare by methodological date.</p><LinePlot points={detail.data.history.map((point) => ({ label: formatDate(point.methodological_date), value: point.average_fare === null ? null : Number(point.average_fare) }))} label={`${effective} fare history`} valueLabel="Average fare" formatValue={formatCurrency} /></section>
          <section className="data-panel"><h2>Source dispersion</h2><p className="support-copy">Observation count by source for the selected route.</p><ul className="plain-list">{detail.data.route.source_dispersion.length ? detail.data.route.source_dispersion.map((source) => <li key={source.source_code}><span>{source.source_code}</span><strong>{source.observation_count}</strong></li>) : <li><span>No source data</span><strong>Pending</strong></li>}</ul><p className="support-copy carrier-note">Carriers: {detail.data.route.carriers.length ? detail.data.route.carriers.join(", ") : "none observed"}</p></section>
          <section className="data-panel span-three" aria-labelledby="lead-title"><div className="section-heading"><div><h2 id="lead-title">Lead-time curve</h2><p>Median fare across the T+1, T+7, T+15, T+30 and T+45 collection windows.</p></div><span className="version-label">Travel {formatDate(detail.data.leadTime.travel_date)}</span></div><LinePlot points={detail.data.leadTime.points.map((point) => ({ label: formatAdvanceWindow(point.advance_window), value: Number(point.median_fare) }))} label={`${effective} lead-time curve`} valueLabel="Median fare" formatValue={formatCurrency} /></section>
        </div> : null}
      </DataState> : null}
    </>
  );
}
