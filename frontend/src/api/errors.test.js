import { describe, expect, it } from 'vitest'

import { ApiError, ERROR_CODES, isCancelledError, toApiError } from './errors.js'

describe('ApiError.fromAxios', () => {
  it('maps a network failure to a helpful message naming the API', () => {
    const error = ApiError.fromAxios({ message: 'Network Error' })
    expect(error.code).toBe(ERROR_CODES.NETWORK_ERROR)
    expect(error.message).toContain('Cannot reach the WindPulse API')
    expect(error.message).toContain('127.0.0.1:8001/api/v1')
  })

  it('maps a timeout', () => {
    const error = ApiError.fromAxios({ code: 'ECONNABORTED', message: 'timeout of 20000ms exceeded' })
    expect(error.code).toBe(ERROR_CODES.TIMEOUT)
  })

  it('keeps the backend error envelope code, message and details', () => {
    const error = ApiError.fromAxios({
      response: {
        status: 409,
        data: {
          error: {
            code: 'DATA_UNAVAILABLE',
            message: 'No forecast selection stored for 2026-01-15.',
            details: { delivery_date: '2026-01-15' },
          },
        },
      },
    })

    expect(error.code).toBe('DATA_UNAVAILABLE')
    expect(error.status).toBe(409)
    expect(error.message).toBe('No forecast selection stored for 2026-01-15.')
    expect(error.details).toEqual({ delivery_date: '2026-01-15' })
    expect(error.isMissingData).toBe(true)
  })

  it('marks validation errors as not missing data', () => {
    const error = ApiError.fromAxios({
      response: {
        status: 422,
        data: { error: { code: 'VALIDATION_ERROR', message: 'limit too large', details: null } },
      },
    })
    expect(error.code).toBe(ERROR_CODES.VALIDATION_ERROR)
    expect(error.isMissingData).toBe(false)
  })

  it('falls back to SERVER_ERROR for an unenveloped 5xx', () => {
    const error = ApiError.fromAxios({ response: { status: 500, data: 'oops' } })
    expect(error.code).toBe(ERROR_CODES.SERVER_ERROR)
    expect(error.status).toBe(500)
    expect(error.message).toBe('The WindPulse API failed while handling this request.')
  })

  it('recognises cancellation', () => {
    const error = ApiError.fromAxios({ code: 'ERR_CANCELED', message: 'canceled' })
    expect(error.isCancelled).toBe(true)
    expect(isCancelledError(error)).toBe(true)
  })
})

describe('toApiError', () => {
  it('passes ApiError through', () => {
    const original = new ApiError({ code: 'NOT_FOUND', message: 'missing' })
    expect(toApiError(original)).toBe(original)
  })

  it('wraps an unknown thrown value', () => {
    const wrapped = toApiError(new Error('boom'))
    expect(wrapped).toBeInstanceOf(ApiError)
    expect(wrapped.message).toBe('boom')
  })
})
