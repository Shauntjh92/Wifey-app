import MallCard from './MallCard'

export default function MallResults({ response }) {
  if (!response) return null

  const { results, unmatched_stores } = response

  return (
    <div className="mt-8">
      {unmatched_stores.length > 0 && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
          <strong>No match found for:</strong>{' '}
          {unmatched_stores.join(', ')}
        </div>
      )}

      {results.length === 0 ? (
        <p className="text-center text-gray-500 py-8">
          No malls found containing those stores. Try gathering data first on the Admin page.
        </p>
      ) : (
        <>
          <p className="text-sm text-gray-500 mb-3">
            Found <strong>{results.length}</strong> mall{results.length !== 1 ? 's' : ''}, ranked by matches
          </p>
          <div className="flex flex-col gap-4">
            {results.map((r) => (
              <MallCard key={r.mall.id} result={r} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
