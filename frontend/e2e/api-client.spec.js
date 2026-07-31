import { test, expect } from '@playwright/test'

test('原生 fetch 适配器保持查询、响应与错误契约', async ({ page }) => {
  let contractUrl = null
  await page.route('**/api/__client_contract*', async (route) => {
    contractUrl = new URL(route.request().url())
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true }),
    })
  })
  await page.route('**/api/__client_error*', async (route) => {
    await route.fulfill({
      status: 422,
      contentType: 'application/problem+json',
      body: JSON.stringify({ detail: '参数无效' }),
    })
  })

  await page.goto('/')
  const result = await page.evaluate(async () => {
    const { api } = await import('/src/api/client.js')
    const success = await api.get('/__client_contract', {
      params: {
        zero: 0,
        empty: '',
        query: '秦 汉&唐',
        nil: null,
        missing: undefined,
      },
    })

    let failure = null
    try {
      await api.get('/__client_error')
    } catch (error) {
      failure = {
        name: error.name,
        status: error.status,
        responseStatus: error.response?.status,
        responseData: error.response?.data,
      }
    }
    return {
      success: {
        data: success.data,
        status: success.status,
        headersIsNative: success.headers instanceof Headers,
      },
      failure,
    }
  })

  expect(contractUrl).not.toBeNull()
  expect(contractUrl.searchParams.get('zero')).toBe('0')
  expect(contractUrl.searchParams.get('empty')).toBe('')
  expect(contractUrl.searchParams.get('query')).toBe('秦 汉&唐')
  expect(contractUrl.searchParams.has('nil')).toBe(false)
  expect(contractUrl.searchParams.has('missing')).toBe(false)
  expect(result.success).toEqual({ data: { ok: true }, status: 200, headersIsNative: true })
  expect(result.failure).toEqual({
    name: 'HttpError',
    status: 422,
    responseStatus: 422,
    responseData: { detail: '参数无效' },
  })
})
