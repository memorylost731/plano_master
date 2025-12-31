import { Link } from "react-router-dom";
import { Upload, PencilRuler } from "lucide-react";

export default function Landing() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Start a project — v2</h1>


      <div className="grid gap-4 sm:grid-cols-2">
        {/* Upload plan */}
        <Link
          to="/upload"
          className="rounded-2xl border bg-white p-6 shadow-sm hover:bg-zinc-50"
        >
          <div className="flex items-center gap-3">
            <div className="rounded-xl border p-2">
              <Upload className="h-5 w-5" />
            </div>
            <div>
              <div className="text-lg font-medium">Upload plan</div>
              <div className="text-sm text-zinc-600">
                Upload PDF / JPG / PNG floor plan
              </div>
            </div>
          </div>
        </Link>

        {/* Create plan */}
        <Link
          to="/create"
          className="rounded-2xl border bg-white p-6 shadow-sm hover:bg-zinc-50"
        >
          <div className="flex items-center gap-3">
            <div className="rounded-xl border p-2">
              <PencilRuler className="h-5 w-5" />
            </div>
            <div>
              <div className="text-lg font-medium">Create a plan</div>
              <div className="text-sm text-zinc-600">
                Start from scratch in the editor
              </div>
            </div>
          </div>
        </Link>
      </div>
    </div>
  );
}
