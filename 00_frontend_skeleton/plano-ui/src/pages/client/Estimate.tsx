import { useMemo } from "react";
import { Link } from "react-router-dom";
import { FileText } from "lucide-react";

import {
  MAIN_SERVICES,
  usePlannerState,
} from "../../state/plannerState";

type EstimateRow = {
  key: string;
  description: string;
  unit: string;
  qty: number;
  rate: number;
  amount: number;
};

function formatNumber(value: number) {
  return (Math.round(value * 100) / 100).toFixed(2);
}

export default function Estimate() {
  const { committedLedger, projectTotalM2 } = usePlannerState();

  const rows = useMemo<EstimateRow[]>(() => {
    return committedLedger.map((entry) => {
      const serviceLabel =
        MAIN_SERVICES.find((service) => service.key === entry.service)?.label ||
        entry.service;

      const rate = 0;
      const amount = entry.totalM2 * rate;

      return {
        key: entry.ledgerId,
        description: `${serviceLabel} — ${entry.subService} — ${entry.materialLabel}`,
        unit: "m²",
        qty: entry.totalM2,
        rate,
        amount,
      };
    });
  }, [committedLedger]);

  const totalAmount = useMemo(() => {
    const sum = rows.reduce((acc, row) => acc + row.amount, 0);
    return Math.round(sum * 100) / 100;
  }, [rows]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="rounded-xl border bg-white p-2">
          <FileText className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold">Estimate</h1>
          <div className="text-sm text-zinc-600">
            Ledger-driven BOQ / cost breakdown
          </div>
        </div>
      </div>

      <div className="rounded-2xl border bg-white shadow-sm overflow-hidden">
        <div className="border-b px-4 py-3 text-sm font-semibold">
          Items
        </div>

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
              {rows.length === 0 ? (
                <tr className="border-t">
                  <td className="px-3 py-4 text-zinc-500" colSpan={5}>
                    No committed services yet.
                  </td>
                </tr>
              ) : (
                <>
                  {rows.map((row) => (
                    <tr key={row.key} className="border-t">
                      <td className="px-3 py-2">{row.description}</td>
                      <td className="px-3 py-2 text-center">{row.unit}</td>
                      <td className="px-3 py-2 text-center">
                        {formatNumber(row.qty)}
                      </td>
                      <td className="px-3 py-2 text-center">
                        {formatNumber(row.rate)}
                      </td>
                      <td className="px-3 py-2 text-right">
                        {formatNumber(row.amount)}
                      </td>
                    </tr>
                  ))}

                  <tr className="border-t bg-zinc-50/60">
                    <td className="px-3 py-2 font-semibold">Total m²</td>
                    <td className="px-3 py-2" />
                    <td className="px-3 py-2 text-center font-semibold">
                      {formatNumber(projectTotalM2)}
                    </td>
                    <td className="px-3 py-2" />
                    <td className="px-3 py-2" />
                  </tr>

                  <tr className="border-t">
                    <td className="px-3 py-2 font-semibold">Grand Total</td>
                    <td className="px-3 py-2" />
                    <td className="px-3 py-2" />
                    <td className="px-3 py-2" />
                    <td className="px-3 py-2 text-right font-semibold">
                      {formatNumber(totalAmount)}
                    </td>
                  </tr>
                </>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <Link
        to="/planner/3d"
        className="inline-flex items-center rounded-lg border bg-white px-3 py-2 text-sm hover:bg-zinc-50"
      >
        Back to Planner
      </Link>
    </div>
  );
}