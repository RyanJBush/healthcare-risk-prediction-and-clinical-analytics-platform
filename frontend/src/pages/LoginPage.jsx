import { useState } from 'react'

import { apiRequest } from '../api'

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('clinician')
  const [password, setPassword] = useState('clinician123')
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    try {
      const data = await apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      })
      onLogin(data.access_token)
    } catch {
      setError('Unable to sign in with provided credentials.')
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
      <form onSubmit={handleSubmit} className="w-full max-w-md rounded-xl bg-white p-6 shadow">
        <h1 className="mb-2 text-2xl font-semibold">Nova AI Login</h1>
        <p className="mb-6 text-sm text-slate-600">Healthcare risk prediction platform access.</p>
        <label className="mb-3 block text-sm">
          Username
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
          />
        </label>
        <label className="mb-4 block text-sm">
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
          />
        </label>
        {error ? <p className="mb-3 text-sm text-red-600">{error}</p> : null}
        <button type="submit" className="w-full rounded bg-slate-900 px-3 py-2 text-white hover:bg-slate-700">
          Sign in
        </button>
      </form>
    </div>
  )
}
