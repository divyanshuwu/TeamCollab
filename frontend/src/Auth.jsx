
import { useState } from 'react'
import { apiRequest } from './api/client'

function Auth({ onLogin }) {
  const [isRegister, setIsRegister] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (isRegister) {
        await apiRequest('/auth/register', {
          method: 'POST',
          body: JSON.stringify({ name, email, password }),
        })
      }

      const data = await apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })

      if (!data.access_token) {
        throw new Error('Login succeeded, but no access token was returned.')
      }

      localStorage.setItem('access_token', data.access_token)

      const user = await apiRequest('/auth/me')

      onLogin(user)
    } catch (err) {
      localStorage.removeItem('access_token')
      setError(err.message || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1>TeamCollab</h1>

        <h2>{isRegister ? 'Create your account' : 'Welcome back'}</h2>

        <p>
          {isRegister
            ? 'Create an account to start collaborating.'
            : 'Sign in to continue to your workspace.'}
        </p>

        {isRegister && (
          <label>
            Full name
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter your name"
              autoComplete="name"
              required
            />
          </label>
        )}

        <label>
          Email address
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
            required
          />
        </label>

        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your password"
            autoComplete={isRegister ? 'new-password' : 'current-password'}
            required
          />
        </label>

        {error && <div className="auth-error">{error}</div>}

        <button className="auth-submit" type="submit" disabled={loading}>
          {loading
            ? 'Please wait...'
            : isRegister
              ? 'Create Account'
              : 'Sign In'}
        </button>

        <div className="auth-switch">
          {isRegister ? 'Already have an account?' : "Don't have an account?"}

          <button
            type="button"
            onClick={() => {
              setIsRegister(!isRegister)
              setError('')
            }}
          >
            {isRegister ? 'Sign in' : 'Register'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default Auth