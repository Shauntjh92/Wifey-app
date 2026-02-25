import { useState, useEffect, useRef } from 'react'
import { api } from '../api/client'

const MAX_SUGGESTIONS = 8

function fuzzyFilter(query, names) {
  if (!query) return []
  const q = query.toLowerCase()
  const scored = names
    .map((name) => {
      const lower = name.toLowerCase()
      if (lower.startsWith(q)) return { name, score: 2 }
      if (lower.includes(q)) return { name, score: 1 }
      return null
    })
    .filter(Boolean)
  scored.sort((a, b) => b.score - a.score)
  return scored.slice(0, MAX_SUGGESTIONS).map((s) => s.name)
}

export default function StoreSearch({ stores, onChange }) {
  const [input, setInput] = useState('')
  const [allStores, setAllStores] = useState([])
  const [suggestions, setSuggestions] = useState([])
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const [showDropdown, setShowDropdown] = useState(false)
  const inputRef = useRef(null)

  useEffect(() => {
    api.getStores().then((data) => {
      setAllStores(data.map((s) => s.name))
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (input.trim()) {
      const filtered = fuzzyFilter(input, allStores)
      setSuggestions(filtered)
      setShowDropdown(filtered.length > 0)
      setHighlightedIndex(-1)
    } else {
      setSuggestions([])
      setShowDropdown(false)
    }
  }, [input, allStores])

  function addStore(name) {
    const trimmed = name.trim()
    if (trimmed && !stores.includes(trimmed)) {
      onChange([...stores, trimmed])
    }
    setInput('')
    setSuggestions([])
    setShowDropdown(false)
    setHighlightedIndex(-1)
  }

  function removeStore(name) {
    onChange(stores.filter((s) => s !== name))
  }

  function handleKeyDown(e) {
    if (showDropdown && suggestions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setHighlightedIndex((i) => Math.min(i + 1, suggestions.length - 1))
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setHighlightedIndex((i) => Math.max(i - 1, -1))
        return
      }
      if (e.key === 'Escape') {
        setShowDropdown(false)
        setHighlightedIndex(-1)
        return
      }
    }
    if (e.key === 'Enter') {
      e.preventDefault()
      if (highlightedIndex >= 0 && suggestions[highlightedIndex]) {
        addStore(suggestions[highlightedIndex])
      } else {
        addStore(input)
      }
    } else if (e.key === 'Backspace' && input === '' && stores.length > 0) {
      onChange(stores.slice(0, -1))
    }
  }

  function handleBlur() {
    // Delay so onMouseDown on a suggestion fires before we close
    setTimeout(() => {
      setShowDropdown(false)
      setHighlightedIndex(-1)
    }, 150)
  }

  return (
    <div className="relative">
      <div className="flex flex-wrap gap-2 items-center border border-gray-300 rounded-lg px-3 py-2 bg-white focus-within:ring-2 focus-within:ring-blue-500 min-h-12">
        {stores.map((store) => (
          <span
            key={store}
            className="flex items-center gap-1 bg-blue-100 text-blue-800 text-sm font-medium px-2.5 py-1 rounded-full"
          >
            {store}
            <button
              type="button"
              onClick={() => removeStore(store)}
              className="text-blue-600 hover:text-blue-900 ml-1 font-bold leading-none"
              aria-label={`Remove ${store}`}
            >
              ×
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          onFocus={() => { if (suggestions.length > 0) setShowDropdown(true) }}
          placeholder={stores.length === 0 ? 'Type a store name and press Enter…' : 'Add another store…'}
          className="flex-1 min-w-32 outline-none text-sm text-gray-700 placeholder-gray-400 bg-transparent"
        />
      </div>

      {showDropdown && (
        <ul className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-56 overflow-y-auto">
          {suggestions.map((name, i) => (
            <li
              key={name}
              onMouseDown={() => addStore(name)}
              className={`px-4 py-2 text-sm cursor-pointer ${
                i === highlightedIndex
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              {name}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
