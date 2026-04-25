<template>
  <nav class="navbar">
    <div class="container navbar-inner">
      <router-link to="/" class="logo">
        <span class="logo-icon">⚡</span>
        <span class="logo-text">BetAI</span>
      </router-link>

      <div class="nav-links">
        <router-link to="/" class="nav-link" :class="{ active: $route.path === '/' }">Jogos</router-link>
        <router-link to="/alerts" class="nav-link" :class="{ active: $route.path === '/alerts' }">
          Alertas
          <span v-if="alertCount > 0" class="alert-badge">{{ alertCount }}</span>
        </router-link>
        <router-link to="/bookmakers" class="nav-link" :class="{ active: $route.path === '/bookmakers' }">Casas</router-link>
      </div>

      <div class="nav-right">
        <div class="live-indicator">
          <div class="pulse"></div>
          <span>ao vivo</span>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getAlerts } from '../api'

const alertCount = ref(0)

onMounted(async () => {
  try {
    const res = await getAlerts()
    alertCount.value = res.data.total
  } catch (e) {}
})
</script>

<style scoped>
.navbar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(10,10,15,0.85);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
}
.navbar-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  gap: 32px;
}
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  flex-shrink: 0;
}
.logo-icon { font-size: 20px; }
.logo-text {
  font-family: 'Syne', sans-serif;
  font-weight: 800;
  font-size: 20px;
  color: var(--accent);
  letter-spacing: -0.02em;
}
.nav-links {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
}
.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 14px;
  color: var(--text-2);
  text-decoration: none;
  transition: all 0.15s;
}
.nav-link:hover { color: var(--text); background: var(--bg-3); }
.nav-link.active { color: var(--accent); background: var(--accent-dim2); }
.alert-badge {
  background: var(--accent);
  color: #0a0a0f;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 20px;
  font-family: 'DM Mono', monospace;
}
.nav-right { flex-shrink: 0; }
.live-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-3);
  font-family: 'DM Mono', monospace;
}
</style>