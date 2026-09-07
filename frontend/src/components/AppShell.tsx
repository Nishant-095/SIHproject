import { useLayoutEffect, useRef, type PropsWithChildren, type ReactNode } from "react";
import { gsap } from "gsap";
import { NavLink, useLocation } from "react-router-dom";

const navigation = [
  { to: "/", label: "Overview", code: "IDX", icon: <path d="M4 16V9m6 7V4m6 12v-6m4 10H2" /> },
  { to: "/routes", label: "Route explorer", code: "RTE", icon: <><circle cx="5" cy="17" r="2" /><circle cx="19" cy="7" r="2" /><path d="M7 16c3-1 4-7 10-8" /></> },
  { to: "/provenance", label: "Provenance", code: "PRV", icon: <><path d="M6 4v16m0-12h6l3 3h3" /><circle cx="6" cy="4" r="2" /><circle cx="6" cy="20" r="2" /><circle cx="19" cy="11" r="2" /></> },
  { to: "/operations", label: "Operations", code: "OPS", icon: <><path d="M4 6h16M4 12h16M4 18h16" /><circle cx="8" cy="6" r="2" /><circle cx="16" cy="12" r="2" /><circle cx="10" cy="18" r="2" /></> },
] as const;

function NavIcon({ children }: { children: ReactNode }) {
  return <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">{children}</svg>;
}

export function AppShell({ children }: PropsWithChildren) {
  const location = useLocation();
  const shellRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const reduceMotion = typeof window.matchMedia !== "function" || window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion || !shellRef.current) return;
    const context = gsap.context(() => {
      const timeline = gsap.timeline({ defaults: { ease: "expo.out" } });
      timeline
        .fromTo(".page-intro h1", { y: 14, opacity: 0 }, { y: 0, opacity: 1, duration: 0.52 })
        .fromTo(".page-intro .page-summary", { y: 8, opacity: 0 }, { y: 0, opacity: 1, duration: 0.36 }, "-=0.28")
        .fromTo(".route-signal-path", { strokeDasharray: 900, strokeDashoffset: 900 }, { strokeDashoffset: 0, duration: 0.85 }, 0);
    }, shellRef);
    return () => context.revert();
  }, [location.pathname]);

  return (
    <div className="app-shell" ref={shellRef}>
      <a className="skip-link" href="#main-content">Skip to evidence</a>
      <aside className="rail" aria-label="Primary">
        <div className="wordmark">
          <span className="wordmark-mark" aria-hidden="true">
            <svg viewBox="0 0 42 42"><path d="M5 31 15 11h11l11 20M11 24h20" /><circle cx="5" cy="31" r="2" /><circle cx="37" cy="31" r="2" /></svg>
          </span>
          <div>
            <strong>Airfare APIx</strong>
            <span>India / evidence console</span>
          </div>
        </div>
        <nav className="navigation" aria-label="Project sections">
          {navigation.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === "/"}>
              <NavIcon>{item.icon}</NavIcon>
              <span>{item.label}<small>{item.code}</small></span>
            </NavLink>
          ))}
        </nav>
        <div className="rail-note">
          <span className="status-dot" aria-hidden="true" />
          <span>Evidence boundary</span>
          <strong>Synthetic data declared</strong>
        </div>
      </aside>
      <div className="workspace">
        <header className="command-band">
          <div className="command-index"><span>IND</span><span>03 routes</span><span>05 windows</span><span>10:00 IST</span></div>
          <div className="command-state"><span><i aria-hidden="true" /> Public evidence</span><strong>SYNTHETIC</strong><span>Method v0.1</span></div>
        </header>
        <div className="route-signal" aria-hidden="true">
          <svg viewBox="0 0 1200 120" preserveAspectRatio="none"><path className="route-signal-grid" d="M0 78H1200" /><path className="route-signal-path" d="M0 78H210L252 36H520L564 78H828L882 46H1200" /><circle cx="252" cy="36" r="4" /><circle cx="564" cy="78" r="4" /><circle cx="882" cy="46" r="4" /></svg>
        </div>
        <main id="main-content" className="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}
