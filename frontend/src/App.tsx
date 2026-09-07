import { useEffect } from "react";
import { Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { NotFoundPage } from "./pages/NotFoundPage";
import { OperationsPage } from "./pages/OperationsPage";
import { OverviewPage } from "./pages/OverviewPage";
import { ProvenancePage } from "./pages/ProvenancePage";
import { RouteExplorerPage } from "./pages/RouteExplorerPage";

const titles: Record<string, string> = {
  "/": "Overview — Airfare APIx",
  "/routes": "Route explorer — Airfare APIx",
  "/provenance": "Provenance — Airfare APIx",
  "/operations": "Operations — Airfare APIx",
};

function RouteTitle() {
  const location = useLocation();
  useEffect(() => {
    document.title = titles[location.pathname] ?? "Page not found — Airfare APIx";
  }, [location.pathname]);
  return null;
}

export function App() {
  return (
    <AppShell>
      <RouteTitle />
      <Routes>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/routes" element={<RouteExplorerPage />} />
        <Route path="/provenance" element={<ProvenancePage />} />
        <Route path="/operations" element={<OperationsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppShell>
  );
}
