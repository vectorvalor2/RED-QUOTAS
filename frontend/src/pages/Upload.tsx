import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createJob } from '../api'

export default function Upload() {
  const [file, setFile] = useState<File | null>(null)
  const [duration, setDuration] = useState('5.0')
  const [resolution, setResolution] = useState('1920x1080')
  const [fps, setFps] = useState('60')
  const [effects, setEffects] = useState('[]')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return
    setLoading(true)
    try {
      const resp = await createJob(file, JSON.parse(effects), parseFloat(duration), resolution, parseInt(fps, 10))
      // store job id locally for Jobs list
      const jobs = JSON.parse(localStorage.getItem('jobs') || '[]')
      jobs.unshift({ clip_id: resp.clip_id, created_at: resp.created_at })
      localStorage.setItem('jobs', JSON.stringify(jobs))
      navigate(`/jobs/${resp.clip_id}`)
    } catch (err) {
      alert('Failed to create job')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white p-6 rounded shadow">
      <h2 className="text-lg font-medium mb-4">Upload a file to generate a clip</h2>
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">File</label>
          <input type="file" onChange={e => setFile(e.target.files ? e.target.files[0] : null)} />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Effects (JSON array)</label>
          <input className="w-full border rounded px-2 py-1" value={effects} onChange={e => setEffects(e.target.value)} />
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Duration</label>
            <input className="w-full border rounded px-2 py-1" value={duration} onChange={e => setDuration(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Resolution</label>
            <input className="w-full border rounded px-2 py-1" value={resolution} onChange={e => setResolution(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">FPS</label>
            <input className="w-full border rounded px-2 py-1" value={fps} onChange={e => setFps(e.target.value)} />
          </div>
        </div>

        <div>
          <button disabled={loading} className="bg-blue-600 text-white px-4 py-2 rounded">
            {loading ? 'Uploading...' : 'Submit'}
          </button>
        </div>
      </form>
    </div>
  )
}
