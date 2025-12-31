import { Link } from "react-router-dom";
import { usePlannerState } from "../../state/plannerState";

export default function Payment() {
  const { hasAnySelection, selectedCount } = usePlannerState();

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Payment</h1>

      <div className="rounded-2xl border bg-white p-5 shadow-sm space-y-2">
        <div className="text-sm text-zinc-700">
          Selected items: <span className="font-semibold">{selectedCount}</span>
        </div>

        <div className="text-sm text-zinc-600">
          Stripe checkout placeholder (UI only). This page will create a checkout session later.
        </div>
      </div>

      <div className="flex gap-2">
        <Link
          to="/quote"
          className="rounded-lg border bg-white px-3 py-2 text-sm hover:bg-zinc-50"
        >
          Back to Quote
        </Link>

        <Link
          to="/confirmation"
          className={`rounded-lg px-3 py-2 text-sm text-white ${
            hasAnySelection ? "bg-zinc-900" : "bg-zinc-900/40 pointer-events-none"
          }`}
        >
          Confirm Payment
        </Link>
      </div>
    </div>
  );
}
