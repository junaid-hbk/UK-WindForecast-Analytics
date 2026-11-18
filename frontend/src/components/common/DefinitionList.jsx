export default function DefinitionList({ items = [], emptyMessage = 'No definitions available.' }) {
  if (items.length === 0) {
    return <p className="text-xs text-slate-500">{emptyMessage}</p>
  }

  return (
    <dl className="divide-y divide-slate-100">
      {items.map((item) => (
        <div key={item.term} className="grid gap-1 py-2 sm:grid-cols-[9rem_1fr] sm:gap-4">
          <dt className="text-xs font-semibold uppercase tracking-wide text-slate-600">
            {item.term}
          </dt>
          <dd className="text-xs leading-relaxed text-slate-700">{item.description}</dd>
        </div>
      ))}
    </dl>
  )
}
