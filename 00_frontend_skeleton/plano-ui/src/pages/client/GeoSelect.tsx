import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MapPin, Home, Building2, Wrench } from "lucide-react";

const DATA: Record<string, string[]> = {
  Malta: ["Valletta", "Sliema", "St Julian's", "Birkirkara", "Mosta"],
  Italy: ["Rome", "Milan", "Turin", "Naples"],
  UK: ["London", "Manchester", "Birmingham"],
};

type ServiceType = "refurbishing" | "new" | "individual";

export default function GeoSelect() {
  const navigate = useNavigate();

  const countries = useMemo(() => Object.keys(DATA), []);
  const [country, setCountry] = useState("");
  const cities = country ? DATA[country] : [];
  const [city, setCity] = useState("");

  const [serviceType, setServiceType] = useState<ServiceType>("refurbishing");

  const canContinue =
    country.length > 0 &&
    (cities.length === 0 || city.length > 0) &&
    !!serviceType;

  function handleContinue() {
    // Single planner route: React-Planner handles 2D/3D internally.
    navigate("/planner");
  }

  return (
    <div className="landing-bg space-y-8">
      <h1 className="text-2xl font-semibold">Choose location</h1>

      {/* LOCATION */}
      <div className="rounded-2xl border bg-white p-6 shadow-sm space-y-5">
        <div className="flex items-start gap-3">
          <div className="rounded-xl border p-2">
            <MapPin className="h-5 w-5" />
          </div>
          <div>
            <div className="font-medium">Location affects pricing</div>
            <div className="text-sm text-zinc-600">
              Contractors and prices differ by country/city.
            </div>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-2">
            <div className="text-sm font-medium">Country</div>
            <select
              value={country}
              onChange={(e) => {
                setCountry(e.target.value);
                setCity("");
              }}
              className="w-full rounded-lg border bg-white px-3 py-2 text-sm"
            >
              <option value="">Select country…</option>
              {countries.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-2">
            <div className="text-sm font-medium">City</div>
            <select
              value={city}
              onChange={(e) => setCity(e.target.value)}
              disabled={!country || cities.length === 0}
              className="w-full rounded-lg border bg-white px-3 py-2 text-sm disabled:opacity-50"
            >
              <option value="">
                {cities.length ? "Select city…" : "No cities listed"}
              </option>
              {cities.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {/* SERVICE TYPE */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold">Choose service type</h2>

        <div className="grid gap-4 sm:grid-cols-3">
          <button
            type="button"
            onClick={() => setServiceType("refurbishing")}
            className={`rounded-2xl border bg-white p-5 text-left shadow-sm hover:bg-zinc-50 ${
              serviceType === "refurbishing" ? "ring-2 ring-zinc-900" : ""
            }`}
          >
            <div className="flex items-center gap-3">
              <div className="rounded-xl border p-2">
                <Home className="h-5 w-5" />
              </div>
              <div className="font-medium">Refurbishing</div>
            </div>
            <div className="mt-2 text-sm text-zinc-600">
              Renovation / upgrades / finishing.
            </div>
          </button>

          <button
            type="button"
            onClick={() => setServiceType("new")}
            className={`rounded-2xl border bg-white p-5 text-left shadow-sm hover:bg-zinc-50 ${
              serviceType === "new" ? "ring-2 ring-zinc-900" : ""
            }`}
          >
            <div className="flex items-center gap-3">
              <div className="rounded-xl border p-2">
                <Building2 className="h-5 w-5" />
              </div>
              <div className="font-medium">New</div>
            </div>
            <div className="mt-2 text-sm text-zinc-600">
              New build estimate workflow.
            </div>
          </button>

          <button
            type="button"
            onClick={() => setServiceType("individual")}
            className={`rounded-2xl border bg-white p-5 text-left shadow-sm hover:bg-zinc-50 ${
              serviceType === "individual" ? "ring-2 ring-zinc-900" : ""
            }`}
          >
            <div className="flex items-center gap-3">
              <div className="rounded-xl border p-2">
                <Wrench className="h-5 w-5" />
              </div>
              <div className="font-medium">Individual service</div>
            </div>
            <div className="mt-2 text-sm text-zinc-600">
              Single service (tiling, plaster, paint, etc.).
            </div>
          </button>
        </div>

        <button
          disabled={!canContinue}
          onClick={handleContinue}
          className="inline-flex items-center rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Continue
        </button>
      </div>
    </div>
  );
}
