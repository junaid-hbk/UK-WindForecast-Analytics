import axios from 'axios'

import { apiBaseUrl, apiTimeoutMs } from './config.js'
import { ApiError } from './errors.js'

export { apiBaseUrl, apiTimeoutMs } from './config.js'

/**
 * Single Axios instance for the whole application.
 *
 * Every rejection is normalised to `ApiError` so components can render the
 * backend's structured error envelope without knowing about Axios.
 */
export const http = axios.create({
  baseURL: apiBaseUrl,
  timeout: apiTimeoutMs,
  headers: { Accept: 'application/json' },
})

http.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(ApiError.fromAxios(error)),
)
