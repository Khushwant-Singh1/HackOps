"use client"

import React, { createContext, useContext, useEffect, useState } from "react"
import { api, tokenStorage } from "@/lib/api"

interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  role: string
  tenant_id?: string
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>
  register: (data: { email: string; password: string; first_name: string; last_name: string }) => Promise<{ success: boolean; error?: string }>
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Check if user is authenticated on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = tokenStorage.getToken()
      if (token) {
        // Verify token and get user profile
        const response = await api.users.getProfile()
        if (response.data) {
          setUser(response.data)
        } else {
          // Token is invalid, remove it
          tokenStorage.removeTokens()
        }
      }
      setIsLoading(false)
    }

    checkAuth()
  }, [])

  const login = async (email: string, password: string) => {
    setIsLoading(true)
    try {
      const response = await api.auth.login(email, password)
      
      if (response.error) {
        setIsLoading(false)
        return { success: false, error: response.error }
      }

      if (response.data?.token) {
        tokenStorage.setToken(response.data.token)
        if (response.data.refresh_token) {
          tokenStorage.setRefreshToken(response.data.refresh_token)
        }
        
        // Get user profile after successful login
        const profileResponse = await api.users.getProfile()
        if (profileResponse.data) {
          setUser(profileResponse.data)
        }
        
        setIsLoading(false)
        return { success: true }
      } else {
        setIsLoading(false)
        return { success: false, error: "Login failed" }
      }
    } catch (error) {
      setIsLoading(false)
      return { 
        success: false, 
        error: error instanceof Error ? error.message : "Login failed" 
      }
    }
  }

  const register = async (data: { 
    email: string
    password: string
    first_name: string
    last_name: string 
  }) => {
    setIsLoading(true)
    try {
      const response = await api.auth.register(data)
      
      if (response.error) {
        setIsLoading(false)
        return { success: false, error: response.error }
      }

      if (response.data?.token) {
        tokenStorage.setToken(response.data.token)
        if (response.data.refresh_token) {
          tokenStorage.setRefreshToken(response.data.refresh_token)
        }
        
        // Get user profile after successful registration
        const profileResponse = await api.users.getProfile()
        if (profileResponse.data) {
          setUser(profileResponse.data)
        }
        
        setIsLoading(false)
        return { success: true }
      } else {
        setIsLoading(false)
        return { success: false, error: "Registration failed" }
      }
    } catch (error) {
      setIsLoading(false)
      return { 
        success: false, 
        error: error instanceof Error ? error.message : "Registration failed" 
      }
    }
  }

  const logout = async () => {
    try {
      // Call logout endpoint
      await api.auth.logout()
    } catch (error) {
      // Even if logout fails on server, clear local storage
      console.error("Logout error:", error)
    } finally {
      tokenStorage.removeTokens()
      setUser(null)
    }
  }

  const value: AuthContextType = {
    user,
    isLoading,
    login,
    register,
    logout,
    isAuthenticated: !!user,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}

// Higher-order component for protected routes
export function withAuth<P extends object>(WrappedComponent: React.ComponentType<P>) {
  return function AuthenticatedComponent(props: P) {
    const { isAuthenticated, isLoading } = useAuth()
    
    if (isLoading) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-gray-900"></div>
        </div>
      )
    }
    
    if (!isAuthenticated) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <h1 className="text-2xl font-bold mb-4">Authentication Required</h1>
            <p className="text-gray-600">Please log in to access this page.</p>
          </div>
        </div>
      )
    }
    
    return <WrappedComponent {...props} />
  }
}