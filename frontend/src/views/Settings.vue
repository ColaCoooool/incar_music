<template>
  <div>
    <div class="view-header">
      <div class="view-title">设置</div>
    </div>

    <!-- Library Stats -->
    <div class="stats-grid" v-if="stats">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_songs }}</div>
        <div class="stat-label">歌曲</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.missing_lyrics }}</div>
        <div class="stat-label">缺歌词</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.missing_covers }}</div>
        <div class="stat-label">缺封面</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ cacheStats.total_size_mb || 0 }}MB</div>
        <div class="stat-label">缓存</div>
      </div>
    </div>

    <!-- Scraper -->
    <div class="settings-group">
      <div class="settings-group-title">🎵 音乐爬取</div>
      <div style="padding: 0 4px;">
        <input
          v-model="scrapeUrl"
          type="text"
          placeholder="粘贴 Bilibili 或抖音链接..."
          style="width: 100%; padding: 12px; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); color: var(--text-primary); font-size: 14px; outline: none;"
        />
        <button
          class="btn btn-primary"
          style="width: 100%; margin-top: 8px;"
          @click="scrapeUrl_"
          :disabled="scraping || !scrapeUrl"
        >
          {{ scraping ? '爬取中...' : '📥 爬取音频' }}
        </button>
        <div v-if="scrapeResult" style="margin-top: 8px; font-size: 13px; color: var(--accent);">
          ✅ {{ scrapeResult }}
        </div>
      </div>
    </div>

    <!-- Library Management -->
    <div class="settings-group">
      <div class="settings-group-title">📚 库管理</div>
      <div class="settings-item" @click="scanLibrary">
        <span class="settings-label">🔄 扫描音乐库</span>
        <span class="settings-value">{{ scanning ? '扫描中...' : '' }}</span>
      </div>
      <div class="settings-item" @click="fillMetadata">
        <span class="settings-label">📝 补全元数据</span>
        <span class="settings-value">{{ filling ? '处理中...' : '' }}</span>
      </div>
      <div class="settings-item" @click="clearCache">
        <span class="settings-label">🗑️ 清除缓存</span>
        <span class="settings-value">{{ cacheStats.total_size_mb || 0 }}MB</span>
      </div>
    </div>

    <!-- Cache Settings -->
    <div class="settings-group">
      <div class="settings-group-title">💾 缓存设置</div>
      <div class="settings-item">
        <span class="settings-label">最大缓存</span>
        <span class="settings-value">{{ cacheStats.max_size_mb || 2048 }}MB</span>
      </div>
      <div class="settings-item">
        <span class="settings-label">已用缓存</span>
        <span class="settings-value">{{ cacheStats.total_size_mb || 0 }}MB ({{ cacheStats.usage_percent || 0 }}%)</span>
      </div>
      <div class="settings-item">
        <span class="settings-label">缓存文件数</span>
        <span class="settings-value">{{ cacheStats.file_count || 0 }}</span>
      </div>
    </div>

    <!-- Stream Settings -->
    <div class="settings-group">
      <div class="settings-group-title">🔊 音质设置</div>
      <div class="settings-item">
        <span class="settings-label">默认码率</span>
        <span class="settings-value">{{ playerStore.bitrate }}kbps</span>
      </div>
      <div style="display: flex; gap: 8px; padding: 0 4px;">
        <button
          v-for="br in [128, 192, 320]"
          :key="br"
          class="btn"
          :class="playerStore.bitrate === br ? 'btn-primary' : 'btn-secondary'"
          @click="playerStore.bitrate = br"
        >
          {{ br }}kbps
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { usePlayerStore } from '../stores/player'

const playerStore = usePlayerStore()

const stats = ref(null)
const cacheStats = ref({})
const scrapeUrl = ref('')
const scrapeResult = ref('')
const scraping = ref(false)
const scanning = ref(false)
const filling = ref(false)

async function loadStats() {
  try {
    const [statsResp, cacheResp] = await Promise.all([
      fetch('/api/library/stats'),
      fetch('/api/stream/cache/stats'),
    ])
    stats.value = await statsResp.json()
    cacheStats.value = await cacheResp.json()
  } catch (err) {
    console.error('Failed to load settings:', err)
  }
}

async function scrapeUrl_() {
  if (!scrapeUrl.value) return
  scraping.value = true
  scrapeResult.value = ''
  try {
    const resp = await fetch('/api/scraper/auto', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: scrapeUrl.value }),
    })
    const data = await resp.json()
    if (resp.ok) {
      scrapeResult.value = `${data.title} - ${data.artist}`
      scrapeUrl.value = ''
    } else {
      scrapeResult.value = `❌ ${data.detail || '爬取失败'}`
    }
  } catch (err) {
    scrapeResult.value = '❌ 网络错误'
  }
  scraping.value = false
}

async function scanLibrary() {
  scanning.value = true
  await fetch('/api/library/scan', { method: 'POST' })
  setTimeout(async () => {
    await loadStats()
    scanning.value = false
  }, 3000)
}

async function fillMetadata() {
  filling.value = true
  await fetch('/api/library/metadata/fill', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  setTimeout(async () => {
    await loadStats()
    filling.value = false
  }, 5000)
}

async function clearCache() {
  await fetch('/api/stream/cache/clear', { method: 'POST' })
  await loadStats()
}

onMounted(() => loadStats())
</script>
