import { useCallback, useEffect, useRef, useState } from 'react'

import { isCancelledError, toApiError } from '../api/index.js'

/**
 * Run one API call, with cancellation, retry and "keep previous data" semantics.
 *
 * `loader` receives an AbortSignal and must return `{ data, meta }`.
 * The effect re-runs whenever `deps` change, so callers pass primitives only.
 */
export function useApiResource(loader, deps = [], { enabled = true } = {}) {
  const loaderRef = useRef(loader)
  loaderRef.current = loader

  const [state, setState] = useState(() => ({
    data: null,
    meta: {},
    error: null,
    isLoading: enabled,
  }))
  const [reloadToken, setReloadToken] = useState(0)

  const reload = useCallback(() => setReloadToken((token) => token + 1), [])

  useEffect(() => {
    if (!enabled) {
      setState((previous) => ({ ...previous, data: null, meta: {}, error: null, isLoading: false }))
      return undefined
    }

    const controller = new AbortController()
    let active = true

    setState((previous) => ({ ...previous, isLoading: true, error: null }))

    Promise.resolve(loaderRef.current(controller.signal))
      .then((result) => {
        if (!active) return
        setState({
          data: result?.data ?? null,
          meta: result?.meta ?? {},
          error: null,
          isLoading: false,
        })
      })
      .catch((thrown) => {
        if (!active || isCancelledError(thrown)) return
        const error = toApiError(thrown)
        if (error.isCancelled) return
        setState({ data: null, meta: {}, error, isLoading: false })
      })

    return () => {
      active = false
      controller.abort()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled, reloadToken])

  return { ...state, reload }
}
