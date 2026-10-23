import { useState } from 'react'
import { apiRequest } from './api/client'
import { supabase } from './utils/supabase'

function Auth({ onLogin }) {
  const [isRegister, setIsRegister] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setNotice('')
    setLoading(true)

    try {
      if (isRegister) {
        const { data, error: signUpError } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { name } },
        })

        if (signUpError) throw signUpError
        if (!data.session) {
          setNotice('Check your email to confirm your account, then sign in.')
          return
        }
      } else {
        const { error: signInError } = await supabase.auth.signInWithPassword({
          email,
          password,
        })
        if (signInError) throw signInError
      }

      const user = await apiRequest('/auth/me')
      onLogin(user)
    } catch (submitError) {
      setError(submitError.message || 'Something went wrong. Please try again.')
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
              onChange={(event) => setName(event.target.value)}
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
            onChange={(event) => setEmail(event.target.value)}
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
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter your password"
            autoComplete={isRegister ? 'new-password' : 'current-password'}
            required
          />
        </label>

        {notice && <div role="status">{notice}</div>}
        {error && <div className="auth-error" role="alert">{error}</div>}

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
              setIsRegister((current) => !current)
              setError('')
              setNotice('')
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
