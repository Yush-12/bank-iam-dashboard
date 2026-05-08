export const severityPill = (severity) => {
  if (severity === "critical") return "bg-red-500/10 text-red-400 border border-red-500/20";
  if (severity === "high") return "bg-orange-500/10 text-orange-400 border border-orange-500/20";
  if (severity === "medium") return "bg-amber-500/10 text-amber-400 border border-amber-500/20";
  return "bg-green-500/10 text-green-400 border border-green-500/20";
};

export const statusPill = (status) => {
  if (status === "active") return "bg-green-500/10 text-green-400 border border-green-500/20";
  if (status === "terminated") return "bg-red-500/10 text-red-400 border border-red-500/20";
  if (status === "on_leave") return "bg-amber-500/10 text-amber-400 border border-amber-500/20";
  if (status === "suspended") return "bg-orange-500/10 text-orange-400 border border-orange-500/20";
  return "bg-slate-500/10 text-slate-400 border border-slate-500/20";
};

export const healthColor = (score) => {
  if (score >= 70) return "text-green-400";
  if (score >= 40) return "text-amber-400";
  return "text-red-400";
};

export const healthBadge = (score) => {
  if (score >= 70) return "bg-green-500/10 text-green-400 border border-green-500/20";
  if (score >= 40) return "bg-amber-500/10 text-amber-400 border border-amber-500/20";
  return "bg-red-500/10 text-red-400 border border-red-500/20";
};

export const riskBar = (score) => {
  if (score >= 75) return "bg-red-500";
  if (score >= 50) return "bg-orange-500";
  if (score >= 30) return "bg-amber-500";
  return "bg-green-500";
};
