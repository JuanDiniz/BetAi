import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 10000,
})

export const getGames = (sport = null, limit = 50) => {
  const params = { limit }
  if (sport) params.sport = sport
  return api.get('/games', { params })
}

export const getGame = (id) => api.get(`/games/${id}`)
export const getAlerts = (limit = 20) => api.get('/alerts', { params: { limit } })
export const getSports = () => api.get('/sports')
export const getBookmakers = () => api.get('/bookmakers')

export default api