import { useLayoutEffect, useRef } from "react";
import { gsap } from "gsap";

type Point = { label: string; value: number | null };

type Props = {
  points: Point[];
  label: string;
  valueLabel: string;
  formatValue?: (value: number) => string;
};

export function LinePlot({ points, label, valueLabel, formatValue = String }: Props) {
  const plotRef = useRef<SVGSVGElement>(null);
  const available = points.filter((point): point is { label: string; value: number } => point.value !== null);
  const values = available.map((point) => point.value);
  const min = values.length ? Math.min(...values) : 0;
  const max = values.length ? Math.max(...values) : 0;
  const range = max - min || 1;
  const coords = points.map((point, index) => ({
    ...point,
    x: 38 + (index / Math.max(points.length - 1, 1)) * 524,
    y: point.value === null ? null : 158 - ((point.value - min) / range) * 118,
  }));
  const path = coords.map((point, index) => point.y === null ? "" : `${index > 0 && coords[index - 1].y !== null ? "L" : "M"}${point.x},${point.y}`).join(" ");
  const first = available[0];
  const latest = available[available.length - 1];

  useLayoutEffect(() => {
    if (!plotRef.current || typeof window.matchMedia !== "function" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const context = gsap.context(() => {
      gsap.fromTo(".plot-line", { strokeDasharray: 900, strokeDashoffset: 900 }, { strokeDashoffset: 0, duration: 0.72, ease: "expo.out" });
      gsap.fromTo(".plot-point", { scale: 0, transformOrigin: "center" }, { scale: 1, duration: 0.28, stagger: 0.045, delay: 0.28, ease: "power2.out" });
    }, plotRef);
    return () => context.revert();
  }, [path]);

  if (available.length < 2) {
    return <div className="chart-empty">At least two published points are needed to draw this trend.</div>;
  }

  return (
    <div className="plot-wrap">
      <svg ref={plotRef} className="line-plot" viewBox="0 0 600 200" role="img" aria-label={label}>
        <g className="plot-grid" aria-hidden="true"><line x1="38" x2="562" y1="40" y2="40" /><line x1="38" x2="562" y1="99" y2="99" /></g>
        <line x1="38" x2="562" y1="158" y2="158" className="plot-axis" />
        <path d={path} className="plot-line" />
        {coords.map((point) => point.y === null ? null : <circle key={`${point.label}-${point.value}`} cx={point.x} cy={point.y} r="4" className="plot-point" tabIndex={0} role="img" aria-label={`${point.label}: ${formatValue(point.value!)}`}><title>{point.label}: {formatValue(point.value!)}</title></circle>)}
        <g className="plot-labels" aria-hidden="true">
          <text x="38" y="24">{formatValue(max)}</text><text x="38" y="180">{formatValue(min)}</text>
          {first ? <text x="38" y="196">{first.label}</text> : null}
          {latest && latest !== first ? <text x="562" y="196" textAnchor="end">{latest.label}</text> : null}
        </g>
      </svg>
      <dl className="plot-readout" aria-label={`${label} summary`}><div><dt>First</dt><dd>{first ? `${first.label} / ${formatValue(first.value)}` : "Missing"}</dd></div><div><dt>Latest</dt><dd>{latest ? `${latest.label} / ${formatValue(latest.value)}` : "Missing"}</dd></div><div><dt>Range</dt><dd>{formatValue(min)} – {formatValue(max)}</dd></div></dl>
      <table className="sr-data-table">
        <caption>{label} data</caption>
        <thead><tr><th>Date or window</th><th>{valueLabel}</th></tr></thead>
        <tbody>{points.map((point) => <tr key={`${point.label}-row`}><td>{point.label}</td><td>{point.value === null ? "Missing" : formatValue(point.value)}</td></tr>)}</tbody>
      </table>
    </div>
  );
}
