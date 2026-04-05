import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import ClientLayout from "./app/ClientLayout.tsx";
import GeoSelect from "./pages/client/GeoSelect.tsx";

import Planner from "./pages/client/Planner.tsx";
import Estimate from "./pages/client/Estimate.tsx";
import SaasDashboard from "./pages/saas/Dashboard.tsx";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* FULLSCREEN MAP — landing page (no layout chrome) */}
        <Route path="/" element={<GeoSelect />} />

        {/* FULLSCREEN EDITOR ROUTE (NO LAYOUT) */}
        <Route path="/planner" element={<Planner />} />

        {/* Backward compatibility: old URLs redirect to the single planner */}
        <Route path="/planner/2d" element={<Navigate to="/planner" replace />} />
        <Route path="/planner/3d" element={<Navigate to="/planner" replace />} />

        {/* SAAS DASHBOARD (for Ogi sprint) */}
        <Route path="/saas" element={<SaasDashboard />} />

        {/* NORMAL PAGES (WITH LAYOUT) */}
        <Route element={<ClientLayout />}>
          <Route path="/estimate" element={<Estimate />} />

          <Route path="/login" element={<div>Client Login</div>} />
          <Route path="/upload" element={<div>Upload Plan</div>} />
          <Route path="/create" element={<div>Create Plan</div>} />
        </Route>

        <Route path="/admin" element={<div>Admin Dashboard</div>} />
        <Route path="/super-admin" element={<div>Super Admin Dashboard</div>} />
      </Routes>
    </BrowserRouter>
  );
}
