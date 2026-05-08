export default function LoadingSpinner({ label = "Loading..." }) {
  return (
    <div className="flex min-h-[180px] items-center justify-center">
      <div className="flex flex-col items-center gap-3 text-slate-400">
        <div className="spinner" />
        <p className="text-sm font-medium animate-pulse">{label}</p>
      </div>
    </div>
  );
}
