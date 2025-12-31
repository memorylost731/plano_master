import { Link } from "react-router-dom";
import { usePlannerState } from "../../state/plannerState";

export default function Quote() {
  const { selectedCount, hasAnySelection } = usePlannerState();

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Quote Summary</h1>

      <div className="rounded-2xl border bg-white p-5 shadow-sm space-y-2">
        <div className="text-sm text-zinc-700">
          Selected items: <span className="font-semibold">{selectedCount}</span>
        </div>
        {!hasAnySelection ? (
          <div className="text-sm text-zinc-600">
            No services selected. Go back to Planner and select sub-services first.
          </div>
        ) : (
          <div className="text-sm text-zinc-600">
            This page will show the final BOQ totals next (UI only for now).
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <Link
          to="/estimate"
          className="rounded-lg border bg-white px-3 py-2 text-sm hover:bg-zinc-50"
        >
          Back to Estimate
        </Link>

        <Link
          to="/payment"
          className={`rounded-lg px-3 py-2 text-sm text-white ${
            hasAnySelection ? "bg-zinc-900" : "bg-zinc-900/40 pointer-events-none"
          }`}
        >
          Proceed to Payment
        </Link>
      </div>
    </div>
  );
}
