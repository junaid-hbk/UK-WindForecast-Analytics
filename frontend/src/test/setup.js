import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

/**
 * jsdom has no layout engine. Recharts needs a non-zero box and a
 * ResizeObserver to mount, so both are stubbed for unit tests only.
 */
if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}

if (!globalThis.matchMedia) {
  globalThis.matchMedia = (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
    width: 960,
    height: 360,
    top: 0,
    left: 0,
    bottom: 360,
    right: 960,
    x: 0,
    y: 0,
    toJSON: () => ({}),
  })
})
