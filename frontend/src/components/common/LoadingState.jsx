export default function LoadingState({ label = 'Loading data…', rows = 4, compact = false }) {
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <span className="sr-only">Please wait</span>
      {Array.from({ length: rows }).map((_, index) => (
        <div
          key={index}
          className={`${compact ? 'h-6' : 'h-12'} animate-pulse rounded-md bg-slate-100`}
        />
      ))}
    </div>
  )
}
