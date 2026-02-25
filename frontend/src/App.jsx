import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import Home from './pages/Home'
import Admin from './pages/Admin'

function Nav() {
  const { pathname } = useLocation()
  return (
    <nav className="bg-white border-b border-gray-200 px-4 py-3 flex gap-6 text-sm font-medium">
      <Link
        to="/"
        className={pathname === '/' ? 'text-blue-600' : 'text-gray-500 hover:text-gray-900'}
      >
        Search
      </Link>
      <Link
        to="/admin"
        className={pathname === '/admin' ? 'text-blue-600' : 'text-gray-500 hover:text-gray-900'}
      >
        Admin
      </Link>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Nav />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/admin" element={<Admin />} />
      </Routes>
    </BrowserRouter>
  )
}
