import { useEffect } from 'react'

const SUFFIX = 'WindPulse UK'

export function useDocumentTitle(title) {
  useEffect(() => {
    document.title = title ? `${title} · ${SUFFIX}` : SUFFIX
  }, [title])
}
