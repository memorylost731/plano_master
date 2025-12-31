import { BrowserRouter, Routes, Route } from "react-router-dom";

import ClientLayout from "./app/ClientLayout";
import GeoSelect from "./pages/client/GeoSelect";

import Planner2D from "./pages/client/Planner2D";
import Planner3D from "./pages/client/Planner3D";
import Estimate from "./pages/client/Estimate";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* FULLSCREEN EDITOR ROUTES (NO LAYOUT) */}
        <Route path="/planner/2d" element={<Planner2D />} />
        <Route path="/planner/3d" element={<Planner3D />} />

        {/* NORMAL PAGES (WITH LAYOUT) */}
        <Route element={<ClientLayout />}>
          <Route path="/" element={<GeoSelect />} />
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
