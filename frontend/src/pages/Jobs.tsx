import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

type JobItem = {
  clip_id: string
  created_at: string
}

export default function Jobs() {
  const [jobs, setJobs] = useState<JobItem[]>([])

  useEffect(() => {
    const js = JSON.parse(localStorage.getItem('jobs') || '[]')
    setJobs(js)
  }, [])

  return (
    <div className="bg-white p-6 rounded shadow">
      <h2 className="text-lg font-medium mb-4">Your Jobs</h2>
      {jobs.length === 0 ? (
        <p>No jobs yet. Upload a file to get started.</p>
      ) : (
        <ul className="space-y-2">
          {jobs.map(j => (
            <li key={j.clip_id} className="p-2 border rounded">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-mono text-sm">{j.clip_id}</div>
                  <div className="text-xs text-gray-500">{j.created_at}</div>
                </div>
                <div>
                  <Link to={`/jobs/${j.clip_id}`} className="text-blue-600">View</Link>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
