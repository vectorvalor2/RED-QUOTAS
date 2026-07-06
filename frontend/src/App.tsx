import React from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import Upload from './pages/Upload'
import Jobs from './pages/Jobs'
import JobDetail from './pages/JobDetail'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-4xl mx-auto py-4 px-6 flex items-center justify-between">
          <h1 className="text-xl font-semibold">RED-QUOTAS</h1>
          <nav className="space-x-4">
            <Link to="/" className="text-blue-600">Upload</Link>
            <Link to="/jobs" className="text-blue-600">Jobs</Link>
          </nav>
        </div>
      </header>

      <main className="max-w-4xl mx-auto p-6">
        <Routes>
          <Route path="/" element={<Upload />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/jobs/:id" element={<JobDetail />} />
        </Routes>
      </main>
    </div>
  )
}
