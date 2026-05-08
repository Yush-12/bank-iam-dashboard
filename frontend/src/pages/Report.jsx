import { useMemo } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { generateReport, getDashboardSummary } from "../api/client";
import ErrorCard from "../components/ErrorCard";

export default function Report() {
  const dashboardQuery = useQuery({
    queryKey: ["dashboard-report-meta"],
    queryFn: getDashboardSummary,
  });

  const reportMutation = useMutation({
    mutationFn: generateReport,
    onSuccess: ({ blob, filename }) => {
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      localStorage.setItem("lastReportGeneratedAt", new Date().toISOString());
    },
  });

  const lastGenerated = useMemo(() => localStorage.getItem("lastReportGeneratedAt"), [reportMutation.isSuccess]);
  const violations = dashboardQuery.data?.sod_violations?.total ?? "-";

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="card p-10 text-center bg-gradient-to-br from-bankSurface to-slate-900">
        <h2 className="text-2xl font-bold text-slate-100 tracking-tight">Access Certification Report</h2>
        <p className="mx-auto mt-4 max-w-xl text-sm text-slate-400 leading-relaxed">
          Generate a comprehensive IAM Access Certification Report. This document maps access violations to 
          <span className="text-bankPrimary font-semibold"> RBI IT Framework</span> and 
          <span className="text-bankPrimary font-semibold"> ISO 27001</span> compliance standards.
        </p>

        <button
          type="button"
          onClick={() => reportMutation.mutate()}
          disabled={reportMutation.isPending}
          className="mt-8 inline-flex items-center gap-2 rounded-lg bg-bankPrimary px-8 py-3 text-sm font-bold text-white shadow-lg shadow-bankPrimary/30 transition-all hover:bg-bankAccent hover:scale-105 disabled:opacity-50 disabled:scale-100"
        >
          {reportMutation.isPending && <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />}
          Generate Full Report
        </button>

        <p className="mt-6 text-[10px] uppercase tracking-widest text-slate-500 font-bold">
          Compliance Standard: RBI-IT-2023 | ISO-27001-A9
        </p>
      </div>

      {reportMutation.isError && <ErrorCard message={reportMutation.error.message} />}
      {dashboardQuery.isError && <ErrorCard message={dashboardQuery.error.message} />}

      <div className="card p-6 bg-slate-900/50">
        <h3 className="text-base font-semibold text-slate-100">Generation History</h3>
        <div className="mt-4 grid gap-4 text-sm md:grid-cols-2">
          <div className="rounded-lg bg-bankBg p-3 border border-bankBorder">
            <p className="text-xs text-slate-500 uppercase font-bold">Last Generated</p>
            <p className="mt-1 text-slate-200 font-medium">{lastGenerated ? new Date(lastGenerated).toLocaleString() : "No history available"}</p>
          </div>
          <div className="rounded-lg bg-bankBg p-3 border border-bankBorder">
            <p className="text-xs text-slate-500 uppercase font-bold">Critical Violations</p>
            <p className="mt-1 text-slate-200 font-medium">{violations} active conflicts identified</p>
          </div>
        </div>
      </div>
    </div>
  );
}
