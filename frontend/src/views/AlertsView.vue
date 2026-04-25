<template>
  <div class="alerts-page">
    <div class="page-header">
      <div class="container">
        <h1 class="page-title">Smart Alerts</h1>
        <p class="page-sub">Value bets detectados automaticamente pelo modelo de IA</p>
      </div>
    </div>

    <div class="container alerts-container">
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
        Carregando alertas...
      </div>

      <div v-else-if="alerts.length === 0" class="empty">
        <div class="empty-icon">🔍</div>
        <div>Nenhum alerta ativo no momento.</div>
        <div class="empty-sub">O sistema analisa novos jogos a cada 5 minutos.</div>
      </div>

      <div v-else class="alerts-list fade-in">
        <div v-for="alert in alerts" :key="alert.id" class="alert-card card">
          <div class="alert-header">
            <div class="alert-type">
              <span class="badge badge-green">🔥 value bet</span>
              <span class="alert-time mono">{{ formatTime(alert.created_at) }}</span>
            </div>
            <div class="edge-badge" :class="edgeClass(alert.edge)">
              +{{ (alert.edge * 100).toFixed(1) }}% edge
            </div>
          </div>

          <div class="alert-title">{{ alert.title }}</div>
          <div class="alert-desc">{{ alert.description }}</div>

          <div class="alert-footer">
            <div class="alert-meta">
              <span class="meta-item">
                <span class="meta-label">Casa</span>
                <span class="meta-value mono">{{ alert.bookmaker }}</span>
              </span>
              <span class="meta-item">
                <span class="meta-label">Resultado</span>
                <span class="meta-value">{{ outcomeLabel(alert.outcome) }}</span>
              </span>
              <span class="meta-item">
                <span class="meta-label">EV</span>
                <span class="meta-value mono accent">+{{ (alert.expected_value * 100).toFixed(1) }}%</span>
              </span>
            </div>

            <a
              v-if="alert.affiliate_link"
              :href="alert.affiliate_link"
              target="_blank"
              class="btn btn-primary"
              @click.stop
            >
              Apostar agora →
            </a>
            <router-link
              v-else
              :to="`/game/${alert.game_id}`"
              class="btn btn-ghost"
            >
              Ver jogo →
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getAlerts } from '../api'

const alerts = ref([])
const loading = ref(true)

const formatTime = (iso) => {
  return new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const outcomeLabel = (o) => ({ home: 'Time da casa', draw: 'Empate', away: 'Visitante' }[o] || o)

const edgeClass = (edge) => {
  if (edge >= 0.3) return 'edge-high'
  if (edge >= 0.15) return 'edge-mid'
  return 'edge-low'
}

onMounted(async () => {
  try {
    const res = await getAlerts(50)
    alerts.value = res.data.alerts
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page-header {
  background: var(--bg-2);
  border-bottom: 1px solid var(--border);
  padding: 32px 0;
  margin-bottom: 32px;
}
.page-title { font-size: 32px; letter-spacing: -0.03em; margin-bottom: 4px; }
.page-sub { color: var(--text-3); font-size: 13px; }
.alerts-container { padding-bottom: 48px; }
.alerts-list { display: flex; flex-direction: column; gap: 10px; }
.alert-card { cursor: default; }
.alert-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}
.alert-type { display: flex; align-items: center; gap: 10px; }
.alert-time { font-size: 11px; color: var(--text-3); }
.edge-badge {
  font-family: 'DM Mono', monospace;
  font-size: 12px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 20px;
}
.edge-high { background: var(--accent-dim); color: var(--accent); }
.edge-mid { background: var(--amber-dim); color: var(--amber); }
.edge-low { background: var(--blue-dim); color: var(--blue); }
.alert-title {
  font-family: 'Syne', sans-serif;
  font-weight: 600;
  font-size: 16px;
  margin-bottom: 6px;
}
.alert-desc { font-size: 13px; color: var(--text-2); margin-bottom: 16px; line-height: 1.5; }
.alert-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.alert-meta { display: flex; gap: 20px; flex-wrap: wrap; }
.meta-item { display: flex; flex-direction: column; gap: 2px; }
.meta-label { font-size: 10px; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.05em; }
.meta-value { font-size: 13px; }
.meta-value.accent { color: var(--accent); }
.empty {
  text-align: center;
  color: var(--text-3);
  padding: 64px;
  font-size: 14px;
}
.empty-icon { font-size: 40px; margin-bottom: 16px; }
.empty-sub { font-size: 12px; margin-top: 6px; }
</style>