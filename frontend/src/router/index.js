import { createRouter, createWebHistory } from 'vue-router'
import GamesView from '../views/GamesView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: GamesView },
    { path: '/alerts', component: () => import('../views/AlertsView.vue') },
    { path: '/game/:id', component: () => import('../views/GameDetailView.vue') },
    { path: '/bookmakers', component: () => import('../views/BookmakersView.vue') },
  ]
})

export default router