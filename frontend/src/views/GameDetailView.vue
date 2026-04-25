<template>
  <div class="game-detail-page">
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      Carregando jogo...
    </div>

    <div v-else-if="game" class="fade-in">
      <!-- Header do jogo -->
      <div class="game-header">
        <div class="container">
          <button class="btn btn-ghost back-btn" @click="$router.back()">← Voltar</button>

          <div class="match-info">
            <div class="match-league">{{ game.sport_title }}</div>
            <div class="match-teams">
              <span class="team-name">{{ game.home_team }}</span>
              <span class="match-vs">×</span>
              <span class="team-name">{{ game.away_team }}</span>
            </div>
            <div class="match-time mono">{{ formatFullTime(game.commence_time) }}</div>
          </div>
        </div>
      </div>

      <div class="container detail-container">
        <!-- Comparador de odds -->
        <div class="section">
          <h2 class="section-title">Comparador de odds</h2>
          <div class="odds-table card">
            <div class="odds-header">
              <div class="col-house">Casa de apostas</div>
              <div class="col-odd">{{ game.home_team }}</div>
              <div class="col-odd">Empate</div>
              <div class="col-odd">{{ game.away_team }}</div>
              <div class="col-action"></div>
            </div>

            <div
              v-for="(odds, bookmaker) in game.bookmakers"
              :key="bookmaker"
              class="odds-row"
              :class="{ 'row-best': isBestBookmaker(bookmaker) }"
            >
              <div class="col-house">
                <span class="bookmaker-name">{{ bookmaker }}</span>
                <span v-if="isBestBookmaker(bookmaker)" class="badge badge-green">melhor</span>
              </div>
              <div class="col-odd">
                <span class="odd-pill" :class="{ best: isBestOdd('home', odds.home) }">
                  {{ odds.home || '-' }}
                </span>
              </div>
              <div class="col-odd">
                <span class="odd-pill" :class="{ best: isBestOdd('draw', odds.draw) }">
                  {{ odds.draw || '-' }}
                </span>
              </div>
              <div class="col-odd">
                <span class="odd-pill" :class="{ best: isBestOdd('away', odds.away) }">
                  {{ odds.away || '-' }}
                </span>
              </div>
              <div class="col-action">
                <a
                  v-if="odds.affiliate_link"
                  :href="odds.affiliate_link"
                  target="_blank"
                  class="btn btn-primary btn-sm"
                >
                  Apostar
                </a>
                <span v-else class="no-link">—</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Alertas do jogo -->
        <div v-if="game.alerts && game.alerts.length > 0" class="section">
          <h2 class="section-title">Value bets detectados</h2>
          <div class="alerts-list">
            <div v-for="alert in game.alerts" :key="alert.id" class="alert-item card">
              <div class="alert-row">
                <span class="badge badge-green">🔥 value bet</span>
                <span class="alert-desc">{{ alert.description }}</span>
                <span class="edge-val mono">+{{ (alert.edge * 100).toFixed(1) }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getGame } from '../api'

const route = useRoute()
const game = ref(null)
const loading = ref(true)

const bestOdds = computed(() => {
  if (!game.value?.bookmakers) return {}
  const result = { home: 0, draw: 0, away: 0 }
  for (const odds of Object.values(game.value.bookmakers)) {
    if (odds.home > result.home) result.home = odds.home
    if (odds.draw > result.draw) result.draw = odds.draw
    if (odds.away > result.away) result.away = odds.away
  }
  return result
})

const isBestOdd = (type, val) => val && val === bestOdds.value[type]

const isBestBookmaker = (bk) => {
  const o = game.value?.bookmakers[bk]
  if (!o) return false
  return isBestOdd('home', o.home) || isBestOdd('draw', o.draw) || isBestOdd('away', o.away)
}

const formatFullTime = (iso) => {
  return new Date(iso).toLocaleString('pt-BR', {
    weekday: 'long', day: '2-digit', month: 'long',
    hour: '2-digit', minute: '2-digit'
  })
}

onMounted(async () => {
  try {
    const res = await getGame(route.params.id)
    game.value = res.data
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.game-header {
  background: var(--bg-2);
  border-bottom: 1px solid var(--border);
  padding: 24px 0 32px;
  margin-bottom: 32px;
}
.back-btn { margin-bottom: 20px; }
.match-league { font-size: 12px; color: var(--text-3); margin-bottom: 12px; }
.match-teams {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.team-name { font-family: 'Syne', sans-serif; font-weight: 700; font-size: 28px; letter-spacing: -0.02em; }
.match-vs { color: var(--text-3); font-size: 20px; }
.match-time { font-size: 13px; color: var(--text-2); }
.detail-container { padding-bottom: 48px; }
.section { margin-bottom: 32px; }
.section-title {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 14px;
  color: var(--text-2);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-family: 'DM Mono', monospace;
}
.odds-table { padding: 0; overflow: hidden; }
.odds-header, .odds-row {
  display: grid;
  grid-template-columns: 200px 1fr 1fr 1fr 100px;
  align-items: center;
  padding: 14px 20px;
  gap: 12px;
}
.odds-header {
  font-size: 11px;
  color: var(--text-3);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border);
  font-family: 'DM Mono', monospace;
}
.odds-row {
  border-bottom: 1px solid var(--border);
  transition: background 0.15s;
}
.odds-row:last-child { border-bottom: none; }
.odds-row:hover { background: var(--bg-3); }
.row-best { background: var(--accent-dim2); }
.col-house { display: flex; align-items: center; gap: 8px; }
.bookmaker-name { font-size: 13px; font-weight: 500; text-transform: capitalize; }
.col-odd { text-align: center; }
.col-action { text-align: right; }
.btn-sm { padding: 5px 12px; font-size: 12px; }
.no-link { color: var(--text-3); font-size: 13px; }
.alerts-list { display: flex; flex-direction: column; gap: 8px; }
.alert-item { padding: 14px 20px; }
.alert-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.alert-desc { flex: 1; font-size: 13px; color: var(--text-2); }
.edge-val { color: var(--accent); font-size: 13px; }
</style>