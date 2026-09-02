import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { authService } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [isAuthenticated, setAuthenticated] = useState(authService.hasSession())
  const login = useCallback(async (credentials) => {
    const session = await authService.login(credentials)
    authService.saveSession(session)
    setAuthenticated(true)
  }, [])
  const signup = useCallback(async (details) => {
    await authService.signup(details)
    await login({ email: details.email, password: details.password })
  }, [login])
  const logout = useCallback(() => { setAuthenticated(false); authService.logout().catch(() => authService.clearSession()) }, [])
  const value = useMemo(() => ({ isAuthenticated, login, signup, logout }), [isAuthenticated, login, signup, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
