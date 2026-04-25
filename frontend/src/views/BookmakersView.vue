<template>
  <div class="bookmakers-page">
    <div class="page-header">
      <div class="container">
        <h1 class="page-title">Casas de apostas</h1>
        <p class="page-sub">Parceiros com links de afiliado — você ganha quando o usuário aposta</p>
      </div>
    </div>

    <div class="container bk-container">
      <div v-if="loading" class="loading"><div class="spinner"></div>Carregando...</div>

      <div v-else class="bk-grid fade-in">
        <div v-for="bk in bookmakers" :key="bk.key" class="bk-card card">
          <div class="bk-header">
            <div class="bk-name">{{ bk.name }}</div>
            <span class="badge" :class="bk.has_affiliate ? 'badge-green' : 'badge-gray'">
              {{ bk.has_affiliate ? '✓ afiliado' : 'sem link' }}
            </span>
          </div>
          <div class="bk-key mono">{{ bk.key }}</div>
          <div class="bk-footer">
            <a v-if="bk.has_affiliate" :href="bk.affiliate_link" target="_blank" class="btn btn-primary">
              Acessar →
            </a>
            <span v-else class="no-affiliate">Configure o link no .env</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getBookmakers } from '../api'

const bookmakers = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await getBookmakers()
    bookmakers.value = res.data.bookmakers
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
.bk-container { padding-bottom: 48px; }
.bk-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
.bk-card { display: flex; flex-direction: column; gap: 10px; }
.bk-header { display: flex; justify-content: space-between; align-items: center; }
.bk-name { font-family: 'Syne', sans-serif; font-weight: 600; font-size: 18px; text-transform: capitalize; }
.bk-key { font-size: 11px; color: var(--text-3); }
.bk-footer { margin-top: 8px; }
.no-affiliate { font-size: 12px; color: var(--text-3); }
</style>