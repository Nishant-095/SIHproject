---
version: alpha
name: "Airfare APIx Flight Recorder"
description: "A light public airfare-index evidence console combining an airline dispatch sheet, an index terminal, and a statistical ledger."
colors:
  primary: "#FF5A1F"
  carbon: "#F4F7F8"
  carbon-deep: "#E8EEF1"
  plate: "#FFFFFF"
  plate-raised: "#EDF3F5"
  ivory: "#122630"
  ivory-soft: "#344C57"
  graphite: "#667B85"
  rule: "#D2DDE1"
  rule-strong: "#9BABB2"
  recorder: "#E84917"
  verified: "#007B75"
  alert: "#B83B35"
  warning: "#956000"
typography:
  display:
    fontFamily: "Source Serif 4, Georgia, serif"
    fontSize: "4.9rem"
    lineHeight: "1.01"
  body:
    fontFamily: "IBM Plex Sans, Segoe UI, sans-serif"
    fontSize: "1.0625rem"
    lineHeight: "1.62"
  data:
    fontFamily: "IBM Plex Mono, monospace"
    fontSize: "0.76rem"
    lineHeight: "1.55"
rounded:
  DEFAULT: "1px"
  compact-status: "1px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "20px"
  xl: "32px"
  xxl: "48px"
  page-max: "96rem"
components:
  app-background:
    backgroundColor: "{colors.carbon}"
    textColor: "{colors.ivory}"
  instrument-plate:
    backgroundColor: "{colors.plate}"
    textColor: "{colors.ivory}"
    rounded: "{rounded.DEFAULT}"
  focus:
    backgroundColor: "{colors.recorder}"
    width: "2px"
  verified-state:
    textColor: "{colors.verified}"
  warning-state:
    textColor: "{colors.warning}"
  failure-state:
    textColor: "{colors.alert}"
  recessed-field:
    backgroundColor: "{colors.carbon-deep}"
    textColor: "{colors.ivory-soft}"
  raised-field:
    backgroundColor: "{colors.plate-raised}"
    textColor: "{colors.ivory}"
  secondary-copy:
    textColor: "{colors.graphite}"
  divider:
    backgroundColor: "{colors.rule}"
  divider-strong:
    backgroundColor: "{colors.rule-strong}"
---

# Airfare APIx Design System

## Overview

### Creative North Star

The interface is a **Flight Recorder / Index Exchange**: an Indian airline
dispatch board meets a securities index terminal and an official statistical
ledger. Its signature is the angular recorder-orange route trace. The trace
connects navigation, route selection, plots, and provenance; it is structural,
not an ornamental flight path.

### Product context and register

- **Audience:** SIH judges, student builders, researchers, and reviewers who
  must verify the index and its evidence chain quickly.
- **Primary job:** Read APIx movement, inspect a fixed route basket, trace an
  observation, and determine whether the latest collection is publishable.
- **Market/locale:** India; English `en-IN`; INR; Asia/Kolkata methodology time.
- **Register:** Public statistical infrastructure, never a booking storefront.
- **Density:** Laptop-first analytical density with usable tablet and phone
  transformations.
- **Anti-references:** No gradients, glass blur, pale floating cards, blobs,
  stock travel photography, generic all-sans styling, fake real-time pulses,
  glow, broad pills, or decorative 3D.
- **Runtime owner:** This file owns visual intent. The one-to-one runtime map is
  the `:root` custom-property block in `frontend/src/styles.css`.

## Colors

Mineral white and cool drafting-paper tones form the flight deck. White plates
and pale blue-grey fields create clear instrument areas; dark aviation ink
carries primary content. Recorder orange is limited to route traces, active
state, and focus. Teal means verified
or healthy; warning amber means limited confidence or synthetic classification;
oxide red means failure or exclusion. Every semantic colour is paired with text,
shape, or border treatment.

## Typography

All three families are self-hosted through Fontsource. Source Serif 4 gives
mastheads, major readings, and section openers an editorial statistical voice.
IBM Plex Sans carries navigation and explanatory copy with open letterforms and
more generous line spacing. IBM Plex Mono owns route codes, dates, status,
fares, versions, tables, and controls. Dense numbers use tabular figures;
technical labels use wider tracking instead of compressed uppercase text.

## Layout

Desktop uses a fixed 14rem command rail, sticky command band, and a 12-column
analytical field capped at 96rem. Panels are divided by one-pixel rules instead
of card gaps and shadows. Primary instruments alone receive a clipped upper-right
corner. Below 1100px the rail compresses; below 760px it becomes a fixed bottom
navigation strip while the document remains the only vertical scroll owner.
Wide semantic tables scroll horizontally inside labelled table regions.

## Elevation & Depth

There are no shadows, translucent sheets, or blur. Depth comes from paper-tone
steps, ruled boundaries, sticky layers, and the route trace. Z-index is reserved
for the rail, command band, sticky table headings, and bottom navigation.

## Shapes

Default radius is one pixel. Compact status marks use the same geometry. The
only circles are route nodes, status lamps, plot points, and the loading spinner,
where the geometry encodes a real point or state. Primary evidence instruments
may use one clipped corner.

## Components

### Navigation and command surfaces

`AppShell` owns the rail, command band, route trace, skip link, responsive bottom
navigation, active-route treatment, and route-entry animation. Every icon has a
visible label and accessible link name. Each route sets a truthful document
title and sends focus to its heading.

### Data instruments

The overview uses one index instrument, ruled movement cells, coverage evidence,
SVG history, semantic fallback tables, and an explicit data-class mark. The route
explorer uses a three-position departure board on desktop and a labelled native
select on mobile. Provenance uses an adjacent master/detail trace rather than
modals. Operations uses a dense readiness strip and ledgers.

### States and feedback

Loading reserves stable space and uses `aria-busy`. Errors persist with a real
Retry action. Empty data has explicit copy. Synthetic, historical, recorded demo,
and live classes remain visibly distinct. Disabled and busy styles are applied
only where those states exist; no fake affordance is rendered.

### Motion

GSAP animates only page-entry headings and the SVG route/plot strokes, inside
`gsap.context()` with cleanup on route change. CSS owns 120–180ms hover/focus
transitions. Nothing loops. `prefers-reduced-motion: reduce` renders the final
state immediately and collapses transition duration.

### Accessibility and resilience

Native landmarks, buttons, links, labels, tables, disclosure, and SVG text
alternatives are preserved. Focus is recorder-orange and cannot be hidden behind
the mobile navigation. Important values are never hover-only. Forced-colors mode
returns colour decisions to the operating system. Print removes the navigation
and command decoration.

## Do's and Don'ts

- **Do:** Keep data class, source health, confidence, and publication state in
  text at the point of use.
- **Do:** Preserve the complete API-derived fact set across breakpoints.
- **Do:** Use ruled composition and the route trace for hierarchy.
- **Don't:** imply live market data while the visible class is synthetic.
- **Don't:** introduce generic cards, gradients, glass, blobs, or excessive
  rounding during future feature work.
- **Don't:** let animation own routing, fetching, calculations, or focus.
