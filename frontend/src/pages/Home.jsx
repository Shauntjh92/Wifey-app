import { useState } from 'react'
import StoreSearch from '../components/StoreSearch'
import MallResults from '../components/MallResults'
import { api } from '../api/client'

export default function Home() {
  const [stores, setStores] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [response, setResponse] = useState(null)

  async function handleSearch() {
    if (stores.length === 0) return
    setLoading(true)
    setError(null)
    try {
      const data = await api.search(stores)
      setResponse(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-12">
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-gray-900">Singapore Mall Finder</h1>
          <p className="mt-2 text-gray-500">
            Find which malls have all the stores you want to visit
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Stores you want to visit
          </label>
          <StoreSearch stores={stores} onChange={setStores} />

          {stores.length > 0 && (
            <p className="mt-2 text-xs text-gray-400">
              {stores.length} store{stores.length !== 1 ? 's' : ''} added · Press Enter to add more
            </p>
          )}

          <button
            onClick={handleSearch}
            disabled={loading || stores.length === 0}
            className="mt-4 w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold py-2.5 px-4 rounded-lg transition-colors"
          >
            {loading ? 'Searching…' : 'Find Malls'}
          </button>

          {error && (
            <p className="mt-3 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
        </div>

        <MallResults response={response} />
      </div>
    </div>
  )
}
