export default function Card({
  title,
  description,
  actions,
  children,
  footer,
  className = '',
  bodyClassName = '',
  as: Tag = 'section',
  id,
}) {
  return (
    <Tag
      id={id}
      className={`rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}
    >
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
          <div className="min-w-0">
            {title && (
              <h2 className="text-sm font-semibold tracking-tight text-slate-900">{title}</h2>
            )}
            {description && (
              <p className="mt-1 max-w-2xl text-xs leading-relaxed text-slate-600">{description}</p>
            )}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={`px-5 py-4 ${bodyClassName}`}>{children}</div>
      {footer && (
        <footer className="border-t border-slate-100 px-5 py-3 text-xs leading-relaxed text-slate-600">
          {footer}
        </footer>
      )}
    </Tag>
  )
}
