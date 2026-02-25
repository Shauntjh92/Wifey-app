export default function MallCard({ result }) {
  const { mall, matched_count, total_requested, matched_stores } = result
  const pct = Math.round((matched_count / total_requested) * 100)

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{mall.name}</h2>
          {mall.address && (
            <p className="text-sm text-gray-500 mt-0.5">{mall.address}</p>
          )}
          {mall.region && (
            <span className="inline-block mt-1 text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
              {mall.region}
            </span>
          )}
        </div>
        <div className="text-right shrink-0">
          <span className="text-2xl font-bold text-blue-600">
            {matched_count}/{total_requested}
          </span>
          <p className="text-xs text-gray-500">stores found</p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mt-3 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-blue-500 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Store chips */}
      <div className="mt-3 flex flex-wrap gap-2">
        {matched_stores.map((ms) => (
          <span
            key={ms.requested}
            className={`flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium ${
              ms.found
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-700 line-through'
            }`}
          >
            {ms.found ? '✓' : '✗'}{' '}
            {ms.found && ms.matched_name !== ms.requested
              ? `${ms.requested} → ${ms.matched_name}`
              : ms.requested}
          </span>
        ))}
      </div>

      {mall.website && (
        <a
          href={mall.website}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 inline-block text-xs text-blue-500 hover:underline"
        >
          Visit website →
        </a>
      )}
    </div>
  )
}
