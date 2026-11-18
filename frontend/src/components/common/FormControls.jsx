const INPUT_CLASS =
  'w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 disabled:cursor-not-allowed disabled:bg-slate-50'

export function Field({ id, label, hint, error, children, className = '' }) {
  const describedBy = [hint ? `${id}-hint` : null, error ? `${id}-error` : null]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={`space-y-1 ${className}`}>
      <label htmlFor={id} className="block text-xs font-semibold text-slate-700">
        {label}
      </label>
      {children({ describedBy: describedBy || undefined, invalid: Boolean(error) })}
      {hint && (
        <p id={`${id}-hint`} className="text-[11px] leading-relaxed text-slate-500">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="text-[11px] font-medium text-rose-700">
          {error}
        </p>
      )}
    </div>
  )
}

export function TextInput({ id, type = 'text', invalid = false, describedBy, className = '', ...rest }) {
  return (
    <input
      id={id}
      type={type}
      aria-invalid={invalid || undefined}
      aria-describedby={describedBy}
      className={`${INPUT_CLASS} ${invalid ? 'border-rose-400' : ''} ${className}`}
      {...rest}
    />
  )
}

export function DateInput({ id, invalid = false, describedBy, className = '', ...rest }) {
  return (
    <TextInput
      id={id}
      type="date"
      invalid={invalid}
      describedBy={describedBy}
      className={className}
      {...rest}
    />
  )
}

export function SelectInput({ id, options = [], invalid = false, describedBy, className = '', ...rest }) {
  return (
    <select
      id={id}
      aria-invalid={invalid || undefined}
      aria-describedby={describedBy}
      className={`${INPUT_CLASS} ${invalid ? 'border-rose-400' : ''} ${className}`}
      {...rest}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  )
}

export function Checkbox({ id, label, description, ...rest }) {
  return (
    <div className="flex items-start gap-2">
      <input
        id={id}
        type="checkbox"
        className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600 accent-[var(--color-brand-600)]"
        {...rest}
      />
      <div>
        <label htmlFor={id} className="text-xs font-medium text-slate-800">
          {label}
        </label>
        {description && <p className="text-[11px] text-slate-500">{description}</p>}
      </div>
    </div>
  )
}

export function formatOptionLabel(policy) {
  return `${policy.name} (${policy.code})`
}
