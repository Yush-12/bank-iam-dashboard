export default function ErrorCard({ message = "Something went wrong." }) {
  return (
    <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 text-red-400">
      <p className="text-sm font-medium">{message}</p>
    </div>
  );
}
