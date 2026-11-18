export default function StatGrid({ children, columns = 4, className = '' }) {
  const cols =
    columns === 3
      ? 'sm:grid-cols-2 xl:grid-cols-3'
      : columns === 2
        ? 'sm:grid-cols-2'
        : 'sm:grid-cols-2 xl:grid-cols-4'

  return <div className={`grid gap-4 ${cols} ${className}`}>{children}</div>
}
