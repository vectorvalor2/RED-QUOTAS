export async function createJob(file: File, effects: any[], duration: number, resolution: string, fps: number) {
  const form = new FormData()
  form.append('file', file)
  form.append('effects', JSON.stringify(effects))
  form.append('duration', String(duration))
  form.append('resolution', resolution)
  form.append('fps', String(fps))

  const resp = await fetch('/api/generate', {
    method: 'POST',
    body: form
  })
  if (!resp.ok) throw new Error('create job failed')
  return resp.json()
}
