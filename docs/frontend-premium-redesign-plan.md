# Premium Frontend Redesign Plan

**Status:** implemented and browser-verified on 6 September 2026  
**Framework boundary:** keep React + Vite + TypeScript; do not use Next.js  
**Estimated change:** 1,450–2,100 added/modified source lines, excluding deleted
legacy CSS and font binaries

## 1. Direct diagnosis of the current interface

The current dashboard is functional, readable, responsive, and honest about
data class. It is not visually premium.

Baseline evidence:

- [`screenshots/current-overview-desktop.png`](screenshots/current-overview-desktop.png)
- [`screenshots/current-routes-desktop.png`](screenshots/current-routes-desktop.png)

Specific problems to remove:

1. The page is a predictable sidebar plus a stack of rounded cards.
2. Large pale empty areas weaken the analytical density.
3. The default system UI type makes the product feel assembled rather than
   art-directed; the existing serif headline is too soft and oversized.
4. Nearly every block has the same radius, border, surface, and importance.
5. The charts behave like supporting widgets rather than the centre of the
   evidence story.
6. The pale paper, blue border, and soft status treatment feel like a generic
   civic dashboard rather than a current aviation-data instrument.
7. Navigation and data changes have almost no spatial continuity or meaningful
   motion.
8. The wordmark and thin circular mark are generic and do not communicate the
   route/window/index idea.

## 2. Creative direction: Flight Recorder / Index Exchange

The interface should feel like three real worlds meeting:

- an Indian airline dispatch and departure-control screen;
- a securities/index terminal where number movement matters;
- an official statistical ledger where every figure has provenance.

The signature is a **route trace**: one angular line that starts at the active
route/window selector, passes through the main APIx plot, and becomes the
provenance chain. It is a real data encoding—not a decorative airplane trail.

The first screen should be recognizable in silhouette: narrow command rail,
large index field, full-width plot, hard evidence strips, and no floating-card
wall.

## 3. Binding anti-pattern rules

- No glassmorphism, backdrop blur, translucent white sheets, or glow fog.
- No gradients, decorative blobs, aurora backgrounds, or fake 3D globes.
- No rounded-everything system. Default radius is `0`; controls may use `2px`.
- No pill-shaped containers except a genuinely compact status token.
- No generic stock airline, airport, or traveller imagery.
- No four identical KPI cards in a row.
- No giant headline consuming the first viewport without useful data.
- No generic system sans as the product's defining voice.
- No bouncy, springy, ornamental, or constant looping animation.
- No colour-only source, warning, or confidence state.
- No fake “real-time” pulse for daily scheduled data.

## 4. Visual system

### Colour

| Token | Value | Use |
|---|---:|---|
| Carbon flight deck | `#0D1217` | Main canvas |
| Instrument plate | `#151C22` | Secondary zones, tables, controls |
| Technical ivory | `#E7E0D0` | Primary text and rare light evidence sheets |
| Recorder orange | `#FF5A1F` | Signature route trace, active state, focus |
| Verified teal | `#55BDB3` | Eligible/healthy/coverage encoding |
| Structural graphite | `#67737C` | Rules, axes, secondary text |
| Alert oxide | `#D6524A` | Failure/exclusion only |
| Deep ink | `#080B0E` | Recessed plot and code fields |

No gradients. Contrast must meet WCAG AA. Orange and teal never carry meaning
without text, shape, or line-style support.

### Typography

Use self-hosted WOFF2 files so the dashboard does not depend on Google Fonts at
runtime:

- **Bodoni Moda** 700/900 for only the product masthead, major numerical
  statements, and section openers;
- **Source Serif 4** 400/600 for body, navigation, explanations, and controls;
- **IBM Plex Mono** 400/500/600 for APIx values, fares, route codes, dates,
  versions, labels, and tables.

This intentionally avoids a generic all-sans dashboard. Data remains stable
with tabular numerals, and decorative high-contrast type never enters dense
tables or small controls.

### Geometry and spacing

- 12-column analytical grid, asymmetric rather than centred-card layout.
- One-pixel ruled divisions; two-pixel active/focus edges.
- Hard corners by default; clipped/notched top-right corners for only primary
  evidence zones.
- Spacing rhythm: 4, 8, 12, 20, 32, 48, 72px.
- Main chart receives 45–55% of the first desktop viewport.
- Dense tables use fixed numeric alignment and sticky headers.
- Surfaces are separated by rules and tonal fields, not shadows.

## 5. Application shell

### Desktop

- Replace the wide sidebar with a 72px icon/code rail plus a 240px contextual
  inspector that appears only when the current page needs it.
- Put system time, active data class, source state, methodology version, and
  export action in a persistent top command band.
- Use route codes and single-purpose line icons; every icon retains a text
  tooltip and accessible name.
- Make the page title part of the data field, not a marketing hero.

### Mobile

- Top command band becomes two rows without horizontal clipping.
- Four primary destinations become a bottom navigation strip.
- Evidence tables keep semantic markup and allow labelled horizontal scroll.
- Current APIx, status, coverage, and data class remain visible before the first
  scroll.

## 6. Page-by-page redesign

### Overview

- One dominant `99.56` index field integrated with a wide time-series plot.
- Daily/weekly/monthly deltas sit on a ruled baseline, not separate cards.
- Coverage becomes a 15-cell route/window instrument below the plot.
- Warnings occupy a persistent right evidence gutter on desktop.
- Direct labels replace legends where possible; the underlying data table
  remains available and keyboard reachable.

### Route explorer

- Route selection becomes a three-position departure-board switch (`DEL–BOM`,
  `DEL–BLR`, `BOM–BLR`).
- Fare history and lead-time curves share one coordinated plot field.
- T+1/T+7/T+15/T+30/T+45 operate as vertical gates on that field.
- Source dispersion and carriers become a narrow evidence tape, not cards.
- Selection changes preserve scale where comparison requires it and announce
  the new route to assistive technology.

### Provenance

- Make the route trace the main interface: `SOURCE -> RAW -> NORMALIZED ->
  CANONICAL -> APIx`.
- Selecting a node reveals an adjacent exact record rather than opening modal
  stacks.
- Parser, normalization, canonicalization, basket, and methodology versions
  align on one version rail.
- Raw JSON is collapsed by default but searchable and copyable when opened.

### Operations

- Use a dense source/run ledger with a fixed status column and explicit run
  counts.
- The top field shows readiness, next scheduled time, most recent run, and the
  first actionable failure.
- Source history becomes a compact reliability strip; no fake continuously
  moving waveform.
- Administrative actions remain outside the public React build unless an
  authenticated server-side boundary is added later.

## 7. Motion system

Add one runtime dependency: `gsap`. Use `gsap.context()` inside React effects so
all animations are reverted on unmount.

### Signature motion

1. **Application entry (650ms):** command rules draw in, then the current APIx
   resolves upward by 12px while the route trace draws across the plot.
2. **Route change (420–560ms):** old series exits in 180ms; scales and route
   code update; the new series draws in using transform/opacity and SVG
   `stroke-dashoffset`.
3. **Provenance inspect (360ms):** the selected trace segment brightens and the
   evidence panel slides 16px from its attached side.
4. **Data refresh (300–500ms):** only changed numeric glyphs tick to their new
   values; unchanged content does not replay.

### Interaction motion

- CSS handles 120–180ms hover, focus, and pressed transitions.
- GSAP handles only sequenced route/page/data narratives.
- Animate transform, opacity, and SVG stroke; avoid `top`, `left`, width, height,
  blur, and large shadow animation.
- Exit never blocks navigation beyond 200ms; loading state takes over if the API
  is slower.
- `prefers-reduced-motion: reduce` renders the final state immediately, keeps
  focus movement predictable, and disables number rolling/line drawing.
- Nothing autoplays forever. No animation is required to read a value.

## 8. Implementation phases and estimated source lines

| Redesign phase | Work | Estimated added/modified LOC | Gate |
|---|---|---:|---|
| F0 — Baseline/freeze | Screenshot matrix, DOM/accessibility inventory, performance baseline | 60–100 docs/tests | Existing behaviour recorded before styling changes |
| F1 — Foundations | Replace tokens, self-host fonts, reset geometry, shared focus/motion utilities | 260–380 | Type samples, contrast, reduced-motion contract pass |
| F2 — Shell | Command band, compact rail, responsive nav, data-class control | 220–320 | All routes and keyboard navigation work at 375/768/1440px |
| F3 — Overview | Index field, chart composition, coverage matrix, evidence gutter | 300–430 | Every existing overview fact remains visible and API-derived |
| F4 — Routes | Departure-board selector, coordinated plots, evidence tape | 240–360 | Route switching and lead-time data pass tests |
| F5 — Provenance/operations | Trace explorer, version rail, run/source ledger | 280–400 | Raw-to-index chain and failures remain inspectable |
| F6 — GSAP motion | Entry, route transition, trace selection, numeric update hooks | 150–240 | No leaked timelines; reduced motion and low-end smoothness pass |
| F7 — QA/polish | Responsive fixes, a11y, browser snapshots, visual regression fixtures | 180–270 | Build/tests/console/keyboard/performance acceptance pass |

Estimated total is not a target to inflate. Replacing and deleting the current
CSS should keep the finished frontend compact.

## 9. Required component boundaries

```text
AppShell
  CommandBand
  NavigationRail
  PageField
    IndexInstrument
    RouteTracePlot
    CoverageMatrix
    EvidenceGutter
    ProvenanceTrace
    OperationsLedger
  DataClassMark
  StatusMark
  AccessibleDataTable
```

Charts remain lightweight SVG/React components unless measured data volume
justifies a chart library. GSAP animates presentation only; it never owns data,
fetching, routing, or calculation state.

## 10. Acceptance checklist

### Visual

- [x] No glass, gradients, blobs, soft floating cards, or broad pill styling.
- [x] Default panel radius is 0–2px; hierarchy works without shadow.
- [x] The first viewport reads as one composed analytical field.
- [x] Typography is visibly art-directed and uses no generic system sans as the
  defining face.
- [x] Overview, routes, provenance, and operations have distinct compositions
  but one system.
- [x] Baseline and final screenshots exist at desktop, tablet, and phone widths.

### Behaviour and accessibility

- [x] Every existing API loading, empty, retry, and error state is preserved.
- [x] Keyboard navigation, visible focus, landmarks, headings, labels, and table
  semantics pass manual review.
- [x] Text contrast is designed for WCAG AA and information is not colour-only.
- [x] Reduced motion eliminates non-essential transforms and count-up effects.
- [x] Direct route refresh and navigation work.
- [x] React effects and GSAP timelines include cleanup.

### Performance

- [x] Production build succeeds and does not ship unused GSAP plugins.
- [x] Self-hosted fonts and loading regions reserve stable layout.
- [x] Route transitions stay responsive and interaction
  is never blocked by an animation.
- [x] SVG plots remain usable with the current dataset and provide a visible
  table/narrative fallback.

## 11. Boundary for the next implementation request

The redesign was explicitly requested after Phase 16 and is now implemented.
`DESIGN.md` is the maintained visual source of truth; future frontend work must
preserve its data-honesty and anti-pattern boundaries.
