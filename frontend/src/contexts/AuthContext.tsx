import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { authService } from '../services/api'
import { message } from 'antd'

interface User {
  id: number
  email: string
  role: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
  isLoading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Проверяем сохраненный токен при загрузке
    const savedToken = localStorage.getItem('token')
    if (savedToken) {
      setToken(savedToken)
      authService.setToken(savedToken)
      // Загружаем информацию о пользователе
      authService
        .getMe()
        .then((userData) => {
          setUser(userData)
        })
        .catch(() => {
          // Токен невалиден, удаляем его
          localStorage.removeItem('token')
          setToken(null)
          authService.setToken(null)
        })
        .finally(() => {
          setIsLoading(false)
        })
    } else {
      setIsLoading(false)
    }
  }, [])

  const login = async (email: string, password: string) => {
    try {
      const response = await authService.login(email, password)
      const newToken = response.access_token
      setToken(newToken)
      localStorage.setItem('token', newToken)
      authService.setToken(newToken)

      const userData = await authService.getMe()
      setUser(userData)
      message.success('Успешный вход в систему')
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Ошибка входа')
      throw error
    }
  }

  const register = async (email: string, password: string) => {
    try {
      await authService.register(email, password)
      message.success('Регистрация успешна. Войдите в систему')
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Ошибка регистрации')
      throw error
    }
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem('token')
    authService.setToken(null)
    message.info('Вы вышли из системы')
  }

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  )
}

