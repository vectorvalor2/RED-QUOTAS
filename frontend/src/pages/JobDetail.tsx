import React, { useEffect, useState, useRef } from 'react'
import { useParams } from 'react-router-dom'

type Clip = {
  clip_id: string
  status: string
  progress?: number
  url?: string
  created_at?: string
  completed_at?: string
  error_message?: string
}

export default function JobDetail() {
  const { id } = useParams()
  const [clip, setClip] = useState<Clip | null>(null)
  const [wsStatus, setWsStatus] = useState('disconnected')
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!id) return
    fetch(`/api/clips/${id}`)
      .then(r => r.json())
      .then(setClip)
      .catch(() => {})

    const ws = new WebSocket((location.protocol === 'https:' ? 'wss' : 'ws') + '://' + location.host + `/ws/clip/${id}`)
    wsRef.current = ws
    ws.onopen = () => setWsStatus('connected')
    ws.onclose = () => setWsStatus('closed')
    ws.onerror = () => setWsStatus('error')
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        if (msg.type === 'progress') {
          setClip(prev => prev ? { ...prev, progress: msg.progress, status: 'processing' } : prev)
        }
      } catch (e) {}
    }

    return () => {
      ws.close()
    }
  }, [id])

  if (!id) return <div>Missing id</div>

  return (
    <div className="bg-white p-6 rounded shadow">
      <h2 className="text-lg font-medium mb-4">Job {id}</h2>
      <div className="space-y-2">
        <div>Status: <strong>{clip ? clip.status : 'loading...'}</strong></div>
        <div>Progress: <strong>{clip && clip.progress !== undefined ? `${clip.progress}%` : 'N/A'}</strong></div>
        <div>WebSocket: <strong>{wsStatus}</strong></div>
        {clip && clip.url && (
          <div>
            <a className="text-blue-600" href={clip.url} target="_blank" rel="noreferrer">Download result</a>
          </div>
        )}
        {clip && clip.error_message && (
          <div className="text-red-600">Error: {clip.error_message}</div>
        )}
      </div>
    </div>
  )
}
