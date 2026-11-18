export default function PageHeader({ eyebrow, title, description, badges, actions }) {
  return (
    <div className="mb-6 flex flex-col gap-4 border-b border-slate-200 pb-5 lg:flex-row lg:items-end lg:justify-between">
      <div className="min-w-0">
        {eyebrow && (
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-brand-700">
            {eyebrow}
          </p>
        )}
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 sm:text-[28px]">
          {title}
        </h1>
        {description && (
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-600">{description}</p>
        )}
        {badges && <div className="mt-3 flex flex-wrap items-center gap-2">{badges}</div>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}
