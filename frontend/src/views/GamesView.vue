<template>
  <div class="games-page">
    <!-- Header -->
    <div class="page-header">
      <div class="container">
        <div class="header-top">
          <div>
            <h1 class="page-title">Jogos de hoje</h1>
            <p class="page-sub">Odds em tempo real de {{ sports.length }} ligas • atualizado a cada 5 min</p>
          </div>
          <div class="header-stats">
            <div class="stat">
              <div class="stat-value mono">{{ games.length }}</div>
              <div class="stat-label">jogos</div>
            </div>
            <div class="stat">
              <div class="stat-value mono accent">{{ valueBets }}</div>
              <div class="stat-label">value bets</div>
            </div>
          </div>
        </div>

        <!-- Filtros de liga -->
        <div class="sport-filters">
          <button class="btn btn-ghost" :class="{ active: !selectedSport }" @click="selectedSport = null">
            Todos
          </button>
          <button
            v-for="s in sports"
            :key="s.key"
            class="btn btn-ghost"
            :class="{ active: selectedSport === s.key }"
            @click="selectedSport = s.key"
          >
            {{ sportEmoji(s.key) }} {{ s.title }}
            <span class="sport-count">{{ s.games }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Jogos -->
    <div class="container games-container">
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
        Carregando jogos...
      </div>

      <div v-else-if="filteredGames.length === 0" class="empty">
        Nenhum jogo encontrado.
      </div>

      <div v-else class="games-grid fade-in">
        <div
          v-for="game in filteredGames"
          :key="game.id"
          class="game-card card"
          @click="$router.push(`/game/${game.id}`)"
        >
          <!-- Liga + horário -->
          <div class="game-meta">
            <span class="game-league">{{ sportEmoji(game.sport_key) }} {{ game.sport_title }}</span>
            <span class="game-time mono">{{ formatTime(game.commence_time) }}</span>
          </div>

          <!-- Times -->
          <div class="game-teams">
            <span class="team home">{{ game.home_team }}</span>
            <span class="vs">×</span>
            <span class="team away">{{ game.away_team }}</span>
          </div>

          <!-- Melhores odds -->
          <div v-if="game.best_odds" class="best-odds">
            <div class="odd-item">
              <span class="odd-label">Casa</span>
              <span class="odd-pill best">{{ game.best_odds.home?.odd }}</span>
              <span class="odd-house">{{ game.best_odds.home?.bookmaker }}</span>
            </div>
            <div class="odd-item">
              <span class="odd-label">Empate</span>
              <span class="odd-pill best">{{ game.best_odds.draw?.odd }}</span>
              <span class="odd-house">{{ game.best_odds.draw?.bookmaker }}</span>
            </div>
            <div class="odd-item">
              <span class="odd-label">Fora</span>
              <span class="odd-pill best">{{ game.best_odds.away?.odd }}</span>
              <span class="odd-house">{{ game.best_odds.away?.bookmaker }}</span>
            </div>
          </div>

          <!-- Value bet indicator -->
          <div v-if="hasValueBet(game)" class="value-tag">
            <span class="badge badge-green">🔥 value bet</span>
          </div>

          <div class="card-arrow">→</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { getGames, getSports, getAlerts } from '../api'

const games = ref([])
const sports = ref([])
const alerts = ref([])
const loading = ref(true)
const selectedSport = ref(null)

const filteredGames = computed(() => {
  if (!selectedSport.value) return games.value
  return games.value.filter(g => g.sport_key === selectedSport.value)
})

const valueBets = computed(() => alerts.value.length)

const hasValueBet = (game) => alerts.value.some(a => a.game_id === game.id)

const formatTime = (iso) => {
  const d = new Date(iso)
  return d.toLocaleString('pt-BR', { weekday: 'short', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const sportEmoji = (key) => {
  const map = {
    soccer_brazil_campeonato: '🇧🇷',
    soccer_brazil_serie_b: '🇧🇷',
    soccer_epl: '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
    soccer_spain_la_liga: '🇪🇸',
    soccer_italy_serie_a: '🇮🇹',
    soccer_germany_bundesliga: '🇩🇪',
    soccer_france_ligue_one: '🇫🇷',
    soccer_uefa_champs_league: '🏆',
    soccer_conmebol_copa_libertadores: '🌎',
  }
  return map[key] || '⚽'
}

onMounted(async () => {
  try {
    const [gamesRes, sportsRes, alertsRes] = await Promise.all([
      getGames(),
      getSports(),
      getAlerts(),
    ])
    games.value = gamesRes.data.games
    sports.value = sportsRes.data.sports
    alerts.value = alertsRes.data.alerts
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page-header {
  background: var(--bg-2);
  border-bottom: 1px solid var(--border);
  padding: 32px 0 0;
  margin-bottom: 32px;
}
.header-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  gap: 16px;
}
.page-title { font-size: 32px; letter-spacing: -0.03em; margin-bottom: 4px; }
.page-sub { color: var(--text-3); font-size: 13px; }
.header-stats { display: flex; gap: 24px; flex-shrink: 0; }
.stat { text-align: right; }
.stat-value { font-size: 28px; font-weight: 700; line-height: 1; }
.stat-value.accent { color: var(--accent); }
.stat-label { font-size: 11px; color: var(--text-3); margin-top: 2px; }
.sport-filters {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 16px;
  scrollbar-width: none;
}
.sport-filters::-webkit-scrollbar { display: none; }
.sport-count {
  background: var(--bg-4);
  color: var(--text-3);
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 4px;
  font-family: 'DM Mono', monospace;
}
.games-container { padding-bottom: 48px; }
.games-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 12px;
}
.game-card {
  cursor: pointer;
  position: relative;
  transition: all 0.2s;
}
.game-card:hover { border-color: var(--border-light); transform: translateY(-2px); }
.game-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.game-league { font-size: 12px; color: var(--text-3); }
.game-time { font-size: 12px; color: var(--text-2); }
.game-teams {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.team { font-family: 'Syne', sans-serif; font-weight: 600; font-size: 15px; }
.vs { color: var(--text-3); font-size: 12px; }
.best-odds {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.odd-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  flex: 1;
  min-width: 70px;
  background: var(--bg-3);
  border-radius: 8px;
  padding: 8px;
}
.odd-label { font-size: 10px; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.05em; }
.odd-house { font-size: 10px; color: var(--text-3); }
.value-tag { margin-top: 12px; }
.card-arrow {
  position: absolute;
  bottom: 16px;
  right: 20px;
  color: var(--text-3);
  font-size: 16px;
  transition: all 0.2s;
}
.game-card:hover .card-arrow { color: var(--accent); transform: translateX(3px); }
.empty {
  text-align: center;
  color: var(--text-3);
  padding: 64px;
  font-size: 14px;
}
</style>