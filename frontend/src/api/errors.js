import axios from 'axios'

import { apiBaseUrl } from './config.js'

export const ERROR_CODES = {
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  INVALID_REQUEST: 'INVALID_REQUEST',
  NOT_FOUND: 'NOT_FOUND',
  DATA_UNAVAILABLE: 'DATA_UNAVAILABLE',
  ADMIN_DISABLED: 'ADMIN_DISABLED',
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT: 'TIMEOUT',
  CANCELLED: 'CANCELLED',
  SERVER_ERROR: 'SERVER_ERROR',
  UNKNOWN: 'UNKNOWN',
}

const FRIENDLY_MESSAGES = {
  [ERROR_CODES.NETWORK_ERROR]: `Cannot reach the WindPulse API at ${apiBaseUrl}. Check that the backend is running and that VITE_API_BASE_URL is correct.`,
  [ERROR_CODES.TIMEOUT]: 'The WindPulse API did not respond in time. Try again, or narrow the date range.',
  [ERROR_CODES.CANCELLED]: 'The request was cancelled.',
  [ERROR_CODES.DATA_UNAVAILABLE]: 'No stored data is available for this request yet.',
  [ERROR_CODES.SERVER_ERROR]: 'The WindPulse API failed while handling this request.',
  [ERROR_CODES.UNKNOWN]: 'Something went wrong while talking to the WindPulse API.',
}

/** Error shape raised by every function in `src/api`. */
export class ApiError extends Error {
  constructor({ code = ERROR_CODES.UNKNOWN, message, details = null, status = null }) {
    super(message || FRIENDLY_MESSAGES[code] || FRIENDLY_MESSAGES[ERROR_CODES.UNKNOWN])
    this.name = 'ApiError'
    this.code = code
    this.details = details
    this.status = status
  }

  get isCancelled() {
    return this.code === ERROR_CODES.CANCELLED
  }

  /** True when the data simply does not exist yet (as opposed to a failure). */
  get isMissingData() {
    return this.code === ERROR_CODES.DATA_UNAVAILABLE
  }

  static fromAxios(error) {
    if (axios.isCancel(error) || error?.code === 'ERR_CANCELED') {
      return new ApiError({ code: ERROR_CODES.CANCELLED, message: FRIENDLY_MESSAGES.CANCELLED })
    }
    if (error?.code === 'ECONNABORTED' || /timeout/i.test(error?.message ?? '')) {
      return new ApiError({ code: ERROR_CODES.TIMEOUT, message: FRIENDLY_MESSAGES.TIMEOUT })
    }
    if (!error?.response) {
      return new ApiError({
        code: ERROR_CODES.NETWORK_ERROR,
        message: FRIENDLY_MESSAGES.NETWORK_ERROR,
        details: error?.message ?? null,
      })
    }

    const status = error.response.status
    const envelope = error.response.data?.error
    const code = envelope?.code || (status >= 500 ? ERROR_CODES.SERVER_ERROR : ERROR_CODES.UNKNOWN)
    const backendMessage = envelope?.message

    return new ApiError({
      code,
      status,
      details: envelope?.details ?? null,
      message:
        backendMessage || FRIENDLY_MESSAGES[code] || `The WindPulse API returned HTTP ${status}.`,
    })
  }

  static cancelled() {
    return new ApiError({ code: ERROR_CODES.CANCELLED, message: FRIENDLY_MESSAGES.CANCELLED })
  }
}

export function isCancelledError(error) {
  return error instanceof ApiError ? error.isCancelled : axios.isCancel(error)
}

/** Turn any thrown value into something safe to render. */
export function toApiError(error) {
  if (error instanceof ApiError) return error
  if (axios.isCancel(error)) return ApiError.cancelled()
  return new ApiError({ message: error?.message })
}
