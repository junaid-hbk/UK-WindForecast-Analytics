import { useEffect, useMemo, useState } from 'react'

import { useAppData } from './useAppData.jsx'

/**
 * Cutoff-policy selection shared by several pages.
 *
 * The initial value comes from `/meta/config`; pages never hard-code a policy.
 */
export function usePolicySelection() {
  const { policies, defaultPolicy } = useAppData()
  const [policy, setPolicy] = useState('')

  useEffect(() => {
    if (!policy && defaultPolicy) setPolicy(defaultPolicy)
  }, [defaultPolicy, policy])

  const selected = useMemo(
    () => policies.find((entry) => entry.code === policy) ?? null,
    [policies, policy],
  )

  return { policy, setPolicy, policies, selected }
}
