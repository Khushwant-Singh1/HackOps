const API_URL = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080"

export interface ApiResponse<T = any> {
  data?: T
  error?: string
  message?: string
}

// Simple token storage for client-side
const TOKEN_STORAGE_KEY = 'hackops_token'
const REFRESH_TOKEN_STORAGE_KEY = 'hackops_refresh_token'

export const tokenStorage = {
  getToken: () => {
    if (typeof window === 'undefined') return null
    return localStorage.getItem(TOKEN_STORAGE_KEY)
  },
  setToken: (token: string) => {
    if (typeof window === 'undefined') return
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
  },
  getRefreshToken: () => {
    if (typeof window === 'undefined') return null
    return localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)
  },
  setRefreshToken: (token: string) => {
    if (typeof window === 'undefined') return
    localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token)
  },
  removeTokens: () => {
    if (typeof window === 'undefined') return
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY)
  }
}

/**
 * Make authenticated API request to Go backend
 */
export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const token = tokenStorage.getToken()
    
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string> || {}),
    }
    
    if (token) {
      headers["Authorization"] = `Bearer ${token}`
    }
    
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    })
    
    if (!response.ok) {
      const errorText = await response.text()
      return {
        error: `HTTP ${response.status}: ${errorText}`,
      }
    }
    
    const data = await response.json()
    return { data }
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "Unknown error occurred",
    }
  }
}

/**
 * API methods for different resources
 */
export const api = {
  // Authentication
  auth: {
    login: (email: string, password: string) => apiRequest("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
    register: (data: { email: string; password: string; first_name: string; last_name: string }) => 
      apiRequest("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    refresh: () => {
      const refreshToken = tokenStorage.getRefreshToken()
      return apiRequest("/api/v1/auth/refresh", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
    },
    logout: () => apiRequest("/api/v1/auth/logout", {
      method: "POST",
    }),
  },
  
  // Users
  users: {
    getProfile: () => apiRequest("/api/v1/users/profile"),
    updateProfile: (data: any) => apiRequest("/api/v1/users/profile", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  },
  
  // Events
  events: {
    list: () => apiRequest("/api/v1/events"),
    get: (id: string) => apiRequest(`/api/v1/events/${id}`),
    create: (data: any) => apiRequest("/api/v1/events", {
      method: "POST", 
      body: JSON.stringify(data),
    }),
    update: (id: string, data: any) => apiRequest(`/api/v1/events/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
    delete: (id: string) => apiRequest(`/api/v1/events/${id}`, {
      method: "DELETE",
    }),
  },
  
  // Teams
  teams: {
    list: (eventId?: string) => apiRequest(`/api/v1/teams${eventId ? `?event_id=${eventId}` : ""}`),
    get: (id: string) => apiRequest(`/api/v1/teams/${id}`),
    create: (data: any) => apiRequest("/api/v1/teams", {
      method: "POST",
      body: JSON.stringify(data),
    }),
    update: (id: string, data: any) => apiRequest(`/api/v1/teams/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
    delete: (id: string) => apiRequest(`/api/v1/teams/${id}`, {
      method: "DELETE",
    }),
  },
  
  // Tenants
  tenants: {
    list: () => apiRequest("/api/v1/tenants"),
    get: (id: string) => apiRequest(`/api/v1/tenants/${id}`),
    create: (data: any) => apiRequest("/api/v1/tenants", {
      method: "POST",
      body: JSON.stringify(data),
    }),
    update: (id: string, data: any) => apiRequest(`/api/v1/tenants/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
    delete: (id: string) => apiRequest(`/api/v1/tenants/${id}`, {
      method: "DELETE",
    }),
  },
}