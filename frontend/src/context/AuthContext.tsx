import { createContext, useContext, useState, useCallback, ReactNode } from 'react'

interface AuthState {
  token: string | null
  username: string | null
  role: string | null
}

interface AuthContextType extends AuthState {
  login: (token: string, username: string, role: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(() => ({
    token: localStorage.getItem('token'),
    username: localStorage.getItem('username'),
    role: localStorage.getItem('role'),
  }))

  const login = useCallback((token: string, username: string, role: string) => {
    localStorage.setItem('token', token)
    localStorage.setItem('username', username)
    localStorage.setItem('role', role)
    setState({ token, username, role })
  }, [])

  const logout = useCallback(() => {
    localStorage.clear()
    setState({ token: null, username: null, role: null })
  }, [])

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be inside AuthProvider')
  return ctx
}
