const ALIGN = {
  left: 'text-left',
  right: 'text-right',
  center: 'text-center',
}

export default function DataTable({
  caption,
  columns,
  rows = [],
  getRowKey,
  emptyMessage = 'No rows to display.',
  dense = false,
  maxHeight,
}) {
  const cellPadding = dense ? 'px-3 py-1.5' : 'px-4 py-2.5'

  return (
    <div
      className="overflow-x-auto"
      style={maxHeight ? { maxHeight, overflowY: 'auto' } : undefined}
    >
      <table className="min-w-full border-collapse text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead className="sticky top-0 z-10 bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500">
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className={`whitespace-nowrap border-b border-slate-200 font-semibold ${cellPadding} ${
                  ALIGN[column.align] ?? ALIGN.left
                }`}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-10 text-center text-sm text-slate-500"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row, index) => (
              <tr
                key={getRowKey ? getRowKey(row, index) : (row.id ?? index)}
                className="hover:bg-slate-50/80"
              >
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={`border-b border-slate-100 align-top text-slate-700 ${cellPadding} ${
                      ALIGN[column.align] ?? ALIGN.left
                    } ${column.numeric ? 'tabular-nums' : ''}`}
                  >
                    {column.render ? column.render(row, index) : row[column.key]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
