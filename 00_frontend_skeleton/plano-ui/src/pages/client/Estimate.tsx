import { Link } from "react-router-dom";
import { FileText } from "lucide-react";

export default function Estimate() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="rounded-xl border bg-white p-2">
          <FileText className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold">Estimate</h1>
          <div className="text-sm text-zinc-600">BOQ / cost breakdown (UI only)</div>
        </div>
      </div>

      <div className="rounded-2xl border bg-white shadow-sm overflow-hidden">
        <div className="border-b px-4 py-3 text-sm font-semibold">Items</div>

        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-zinc-50 text-xs text-zinc-600">
              <tr>
                <th className="px-3 py-2 text-left">Description</th>
                <th className="px-3 py-2 text-center">Unit</th>
                <th className="px-3 py-2 text-center">Qty</th>
                <th className="px-3 py-2 text-center">Rate</th>
                <th className="px-3 py-2 text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t">
                <td className="px-3 py-2">Sample: Painting (internal)</td>
                <td className="px-3 py-2 text-center">m²</td>
                <td className="px-3 py-2 text-center">10</td>
                <td className="px-3 py-2 text-center">12</td>
                <td className="px-3 py-2 text-right">120</td>
              </tr>
              <tr className="border-t">
                <td className="px-3 py-2">Sample: Floor tiles (60×60)</td>
                <td className="px-3 py-2 text-center">m²</td>
                <td className="px-3 py-2 text-center">6</td>
                <td className="px-3 py-2 text-center">35</td>
                <td className="px-3 py-2 text-right">210</td>
              </tr>
              <tr className="border-t">
                <td className="px-3 py-2 font-semibold">Total</td>
                <td className="px-3 py-2" />
                <td className="px-3 py-2" />
                <td className="px-3 py-2" />
                <td className="px-3 py-2 text-right font-semibold">330</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <Link
        to="/planner"
        className="inline-flex items-center rounded-lg border bg-white px-3 py-2 text-sm hover:bg-zinc-50"
      >
        Back to Planner
      </Link>
    </div>
  );
}
