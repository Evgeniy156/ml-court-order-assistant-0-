import axios, { AxiosInstance, AxiosError } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

class ApiService {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Интерсептор для добавления токена
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Интерсептор для обработки ошибок
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Токен истек или невалиден
          localStorage.removeItem('token')
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  setToken(token: string | null) {
    if (token) {
      this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`
    } else {
      delete this.client.defaults.headers.common['Authorization']
    }
  }

  getClient() {
    return this.client
  }
}

export const apiService = new ApiService()

// Сервис авторизации
export const authService = {
  async login(email: string, password: string) {
    const formData = new FormData()
    formData.append('username', email)
    formData.append('password', password)
    const response = await apiService.getClient().post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
    return response.data
  },

  async register(email: string, password: string) {
    const response = await apiService.getClient().post('/auth/register', {
      email,
      password,
    })
    return response.data
  },

  async getMe() {
    const response = await apiService.getClient().get('/auth/me')
    return response.data
  },

  setToken(token: string | null) {
    apiService.setToken(token)
  },
}

// Сервис биллинга
export const billingService = {
  async getBalance() {
    const response = await apiService.getClient().get('/balance')
    return response.data
  },

  async deposit(amount: number) {
    const response = await apiService.getClient().post('/balance/deposit', {
      amount,
    })
    return response.data
  },

  async getTransactions() {
    const response = await apiService.getClient().get('/transactions')
    return response.data
  },
}

// Сервис веб-интерфейса
export const webService = {
  async getDashboard() {
    const response = await apiService.getClient().get('/api/web/dashboard')
    return response.data
  },

  async getHistory(page: number = 1, limit: number = 20) {
    const response = await apiService.getClient().get('/api/web/history', {
      params: { page, limit },
    })
    return response.data
  },

  async uploadFile(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiService.getClient().post('/api/web/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
}

// WebSocket клиент для отслеживания задач
export class WebSocketClient {
  private ws: WebSocket | null = null
  private onMessageCallback: ((data: any) => void) | null = null
  private onErrorCallback: ((error: Error) => void) | null = null
  private onCloseCallback: (() => void) | null = null

  connect(taskId: number, token: string) {
    // Преобразуем HTTP URL в WebSocket URL
    const wsBaseUrl = API_BASE_URL.replace(/^http/, 'ws')
    const wsUrl = `${wsBaseUrl}/api/ws/predictions/${taskId}?token=${token}`
    this.ws = new WebSocket(wsUrl)

    this.ws.onopen = () => {
      console.log(`WebSocket connected for task ${taskId}`)
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (this.onMessageCallback) {
          this.onMessageCallback(data)
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      if (this.onErrorCallback) {
        this.onErrorCallback(new Error('WebSocket connection error'))
      }
    }

    this.ws.onclose = () => {
      console.log(`WebSocket closed for task ${taskId}`)
      if (this.onCloseCallback) {
        this.onCloseCallback()
      }
    }
  }

  onMessage(callback: (data: any) => void) {
    this.onMessageCallback = callback
  }

  onError(callback: (error: Error) => void) {
    this.onErrorCallback = callback
  }

  onClose(callback: () => void) {
    this.onCloseCallback = callback
  }

  send(message: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(message)
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}

