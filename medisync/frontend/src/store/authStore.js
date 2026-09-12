/**
 * Authentication state — persisted to localStorage.
 * Stores tokens and current user across page refreshes.
 */

import { create } from 'zustand'
import { api } from '../utils/api'

const useAuthStore = create((set, get) => ({
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  accessToken: localStorage.getItem('access_token'),
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null })
    try {
      const data = await api.post('/auth/login', { email, password })
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      localStorage.setItem('user', JSON.stringify(data.user))
      set({ user: data.user, accessToken: data.access_token, isLoading: false })
      return data.user
    } catch (err) {
      set({ error: err.message, isLoading: false })
      throw err
    }
  },

  register: async (formData) => {
    set({ isLoading: true, error: null })
    try {
      const data = await api.post('/auth/register', formData)
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      localStorage.setItem('user', JSON.stringify(data.user))
      set({ user: data.user, accessToken: data.access_token, isLoading: false })
      return data.user
    } catch (err) {
      set({ error: err.message, isLoading: false })
      throw err
    }
  },

  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    set({ user: null, accessToken: null })
  },

  clearError: () => set({ error: null }),
}))

export default useAuthStore
