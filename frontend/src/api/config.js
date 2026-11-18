/**
 * Single source of truth for the API location.
 *
 * Kept separate from the Axios client so error formatting can name the API
 * without importing the client (which would create an import cycle).
 */
const DEFAULT_BASE_URL = 'http://127.0.0.1:8000/api/v1'
const DEFAULT_TIMEOUT_MS = 20000

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL
export const apiTimeoutMs = Number(import.meta.env.VITE_API_TIMEOUT_MS) || DEFAULT_TIMEOUT_MS
