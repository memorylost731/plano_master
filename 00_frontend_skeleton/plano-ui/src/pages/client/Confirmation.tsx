import { Link } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import { usePlannerState } from "../../state/plannerState";

export default function Confirmation() {
  const { selectedCount, clearAll } = usePlannerState();

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="rounded-xl border bg-white p-2">
          <CheckCircle2 className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold">Confirmation</h1>
          <div className="text-sm text-zinc-600">Payment successful (UI only)</div>
        </div>
      </div>

      <div className="rounded-2xl border bg-white p-5 shadow-sm space-y-2">
        <div className="text-sm text-zinc-700">
          Selected items in this project: <span className="font-semibold">{selectedCount}</span>
        </div>
        <div className="text-sm text-zinc-600">
          This page will later show project ID, assigned contractor, and receipt.
        </div>
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => clearAll()}
          className="rounded-lg border bg-white px-3 py-2 text-sm hover:bg-zinc-50"
        >
          Start new project (reset selections)
        </button>

        <Link
          to="/"
          className="rounded-lg bg-zinc-900 px-3 py-2 text-sm text-white"
        >
          Back to Home
        </Link>
      </div>
    </div>
  );
}
