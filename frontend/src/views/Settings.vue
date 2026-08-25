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

    <!-- Douyin cookies -->
    <div class="settings-group">
      <div class="settings-group-title">🍪 抖音 Cookies</div>
      <div class="settings-item">
        <span class="settings-label">状态</span>
        <span class="settings-value" :style="cookieStatus && cookieStatus.configured ? 'color: var(--accent);' : ''">
          {{ cookieStatus ? (cookieStatus.configured ? '✅ 已配置' : '未配置') : '...' }}
        </span>
      </div>
      <div style="padding: 0 4px;">
        <input
          ref="cookieInput"
          type="file"
          accept=".txt"
          style="width: 100%; color: var(--text-primary); font-size: 14px;"
          @change="onCookieFile"
        />
        <button
          class="btn btn-primary"
          style="width: 100%; margin-top: 8px;"
          :disabled="!cookieFile"
          @click="uploadCookies"
        >
          📤 上传 cookies.txt
        </button>
        <button
          v-if="cookieStatus && cookieStatus.configured"
          class="btn btn-secondary"
          style="width: 100%; margin-top: 8px;"
          @click="removeCookies"
        >
          🗑️ 删除 cookies
        </button>
        <div style="margin-top: 10px; font-size: 13px; color: var(--text-secondary); line-height: 1.6;">
          抖音反爬需要新鲜 cookies：电脑浏览器登录抖音 → 安装「Get cookies.txt」扩展导出 cookies.txt → 上传。
          文件保存在服务器（NAS），抖音爬取时自动使用。B 站爬取无需 cookies。
        </div>
        <div v-if="cookieMsg" style="margin-top: 8px; font-size: 13px;" :style="cookieMsgOk ? 'color: var(--accent);' : 'color: var(--danger);'">
          {{ cookieMsg }}
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
        <span class="settings-label">🗑️ 清除服务端缓存</span>
        <span class="settings-value">{{ cacheStats.total_size_mb || 0 }}MB</span>
      </div>
    </div>

    <!-- Cache Settings -->
    <div class="settings-group">
      <div class="settings-group-title">💾 服务端缓存（NAS）</div>
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

    <!-- Offline cache (browser/device) -->
    <div class="settings-group">
      <div class="settings-group-title">📴 离线缓存（本机）</div>

      <div v-if="!cacheSupported" class="offline-cache-note">
        离线缓存需要 HTTPS 或 localhost 环境，当前环境不可用。<br />
        通过手机热点 http 访问时，播放过的歌曲不会缓存在本机。
      </div>

      <template v-else>
        <div class="settings-item" v-if="offlineStats.loaded">
          <span class="settings-label">已缓存</span>
          <span class="settings-value">
            {{ offlineStats.count }} 首 · {{ offlineStats.usageMb }} MB / {{ offlineStats.quotaMb }} MB（{{ offlineStats.percent }}%）
          </span>
        </div>

        <div v-if="offlineSongs.length" class="offline-song-list">
          <div v-for="item in offlineSongs" :key="item.songId" class="offline-song-item">
            <img v-if="item.coverUrl" :src="item.coverUrl" class="offline-cover" alt="" />
            <div v-else class="offline-cover offline-cover-ph">🎵</div>
            <div class="offline-info">
              <div class="offline-title">{{ item.title }}</div>
              <div class="offline-meta">{{ item.artist }}</div>
            </div>
            <button class="btn btn-secondary offline-del-btn" @click="removeOffline(item)">删除</button>
          </div>
        </div>
        <div v-else-if="offlineStats.loaded" class="empty-state" style="padding: 24px;">
          <div class="empty-text">暂无离线缓存，播放过的歌曲会自动加入</div>
        </div>

        <div style="padding: 0 4px; margin-top: 10px;">
          <button
            class="btn btn-secondary"
            style="width: 100%;"
            :disabled="!offlineSongs.length"
            @click="clearOffline"
          >
            🗑️ 清空全部离线缓存
          </button>
        </div>
      </template>
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
const cookieStatus = ref(null)
const cookieFile = ref(null)
const cookieMsg = ref('')
const cookieMsgOk = ref(true)
const cookieInput = ref(null)

// ─── Douyin cookies ─────────────────────────────────────────────

async function loadCookieStatus() {
  try {
    const r = await fetch('/api/scraper/cookies')
    cookieStatus.value = await r.json()
  } catch (e) {
    console.error('Failed to load cookie status:', e)
    cookieStatus.value = null
  }
}

function onCookieFile(e) {
  cookieFile.value = e.target.files[0] || null
}

async function uploadCookies() {
  if (!cookieFile.value) return
  const fd = new FormData()
  fd.append('file', cookieFile.value)
  try {
    const r = await fetch('/api/scraper/cookies', { method: 'POST', body: fd })
    const data = await r.json()
    if (r.ok) {
      cookieMsg.value = 'cookies 已保存，抖音爬取将自动使用'
      cookieMsgOk.value = true
      cookieFile.value = null
      if (cookieInput.value) cookieInput.value.value = ''
      await loadCookieStatus()
    } else {
      cookieMsg.value = `❌ ${data.detail || '上传失败'}`
      cookieMsgOk.value = false
    }
  } catch (e) {
    cookieMsg.value = '❌ 网络错误'
    cookieMsgOk.value = false
  }
}

async function removeCookies() {
  if (!window.confirm('删除已保存的抖音 cookies？')) return
  try {
    await fetch('/api/scraper/cookies', { method: 'DELETE' })
    cookieMsg.value = 'cookies 已删除'
    cookieMsgOk.value = true
    await loadCookieStatus()
  } catch (e) {
    cookieMsg.value = '❌ 删除失败'
    cookieMsgOk.value = false
  }
}

// ─── Offline cache (browser/device) ─────────────────────────────
// Must match AUDIO_CACHE in public/sw.js
const AUDIO_CACHE = 'incar-audio-v1'
const cacheSupported = window.isSecureContext && 'caches' in window
const offlineStats = ref({ loaded: false, count: 0, usageMb: '0.0', quotaMb: '0', percent: '0' })
const offlineSongs = ref([])

async function loadOfflineCache() {
  if (!cacheSupported) return
  try {
    const cache = await caches.open(AUDIO_CACHE)
    const keys = await cache.keys()

    // Map cached song ids to song info (one batch request)
    const ids = new Set()
    for (const req of keys) {
      const m = /\/api\/stream\/(\d+)/.exec(req.url)
      if (m) ids.add(Number(m[1]))
    }
    let idMap = {}
    try {
      const resp = await fetch('/api/songs/?page_size=200')
      const songs = await resp.json()
      idMap = Object.fromEntries(songs.map((s) => [s.id, s]))
    } catch (e) {
      console.error('Failed to load song list for offline cache:', e)
    }

    const entries = []
    for (const req of keys) {
      const m = /\/api\/stream\/(\d+)/.exec(req.url)
      if (!m) continue
      const sid = Number(m[1])
      const song = idMap[sid]
      entries.push({
        songId: sid,
        url: req.url,
        title: song ? song.title : `歌曲 #${sid}`,
        artist: song ? song.artist_name : '',
        coverUrl: song && song.cover_url ? song.cover_url : '',
      })
    }

    let usage = 0
    let quota = 0
    if ('storage' in navigator && navigator.storage && navigator.storage.estimate) {
      try {
        const est = await navigator.storage.estimate()
        usage = est.usage || 0
        quota = est.quota || 0
      } catch (e) { /* ignore */ }
    }

    offlineSongs.value = entries
    offlineStats.value = {
      loaded: true,
      count: entries.length,
      usageMb: (usage / 1048576).toFixed(1),
      quotaMb: Math.round(quota / 1048576),
      percent: quota ? ((usage / quota) * 100).toFixed(1) : '0',
    }
  } catch (e) {
    console.error('Failed to load offline cache:', e)
    offlineStats.value.loaded = true
  }
}

async function removeOffline(item) {
  try {
    const cache = await caches.open(AUDIO_CACHE)
    await cache.delete(item.url)
    await loadOfflineCache()
  } catch (e) {
    console.error('Failed to remove offline entry:', e)
  }
}

async function clearOffline() {
  if (!window.confirm('清空全部离线缓存？播放过的歌曲将需要重新联网缓存。')) return
  try {
    const cache = await caches.open(AUDIO_CACHE)
    const keys = await cache.keys()
    await Promise.all(keys.map((k) => cache.delete(k)))
    await loadOfflineCache()
  } catch (e) {
    console.error('Failed to clear offline cache:', e)
  }
}

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
    const data = await resp.json().catch(() => null)
    if (resp.ok && data) {
      scrapeResult.value = `${data.title} - ${data.artist}`
      scrapeUrl.value = ''
    } else {
      scrapeResult.value = `❌ ${data?.detail || `服务器错误 HTTP ${resp.status}，请查看后端日志`}`
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

onMounted(() => {
  loadStats()
  loadOfflineCache()
  loadCookieStatus()
})
</script>
