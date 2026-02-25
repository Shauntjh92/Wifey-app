const BASE = (import.meta.env.VITE_API_BASE_URL ?? '') + '/api'

async function request(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}

export const api = {
  gatherData: () => request('POST', '/data/gather'),
  getStatus: () => request('GET', '/data/status'),
  getMalls: () => request('GET', '/malls'),
  getMall: (id) => request('GET', `/malls/${id}`),
  getStores: () => request('GET', '/stores'),
  search: (stores) => request('POST', '/search', { stores }),
}
