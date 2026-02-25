import { useState, useEffect, useRef } from 'react'
import { api } from '../api/client'

export default function Admin() {
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)
  const intervalRef = useRef(null)

  function startPolling() {
    if (intervalRef.current) return
    intervalRef.current = setInterval(async () => {
      try {
        const s = await api.getStatus()
        setStatus(s)
        if (s.status === 'done' || s.status === 'error' || s.status === 'idle') {
          stopPolling()
        }
      } catch (e) {
        setError(e.message)
        stopPolling()
      }
    }, 2000)
  }

  function stopPolling() {
    clearInterval(intervalRef.current)
    intervalRef.current = null
  }

  useEffect(() => {
    // Load initial status
    api.getStatus().then(setStatus).catch(() => {})
    return () => stopPolling()
  }, [])

  async function handleGather() {
    setError(null)
    try {
      await api.gatherData()
      const s = await api.getStatus()
      setStatus(s)
      startPolling()
    } catch (err) {
      setError(err.message)
    }
  }

  const isRunning = status?.status === 'running'
  const isDone = status?.status === 'done'
  const isError = status?.status === 'error'
  const pct =
    status?.total_malls > 0
      ? Math.round((status.completed_malls / status.total_malls) * 100)
      : 0

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-xl mx-auto px-4 py-12">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Admin — Data Gathering</h1>
        <p className="text-gray-500 text-sm mb-8">
          Trigger web scraping to fetch Singapore mall store directories and populate the database.
        </p>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <button
            onClick={handleGather}
            disabled={isRunning}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white font-semibold py-2.5 px-4 rounded-lg transition-colors"
          >
            {isRunning ? 'Gathering data…' : 'Gather Mall Data'}
          </button>

          {error && (
            <p className="mt-3 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          {status && status.status !== 'idle' && (
            <div className="mt-5">
              <div className="flex justify-between text-sm text-gray-600 mb-1.5">
                <span>
                  {isRunning && status.current_mall
                    ? `Scanning: ${status.current_mall}`
                    : isDone
                    ? 'Complete!'
                    : isError
                    ? `Error: ${status.error}`
                    : 'Starting…'}
                </span>
                <span>
                  {status.completed_malls} / {status.total_malls || '?'} malls
                </span>
              </div>

              <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    isError ? 'bg-red-500' : isDone ? 'bg-green-500' : 'bg-indigo-500'
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>

              {isDone && (
                <p className="mt-3 text-sm text-green-700 bg-green-50 rounded-lg px-3 py-2">
                  Data gathering complete! {status.completed_malls} malls processed.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
