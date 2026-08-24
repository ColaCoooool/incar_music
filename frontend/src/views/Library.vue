<template>
  <div>
    <!-- Header -->
    <div class="view-header">
      <div class="view-title">曲库</div>
      <div class="search-bar">
        <span class="search-icon">🔍</span>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索歌曲、歌手..."
          @input="debouncedSearch"
        />
      </div>
    </div>

    <!-- Stats -->
    <div class="stats-grid" v-if="stats">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_songs }}</div>
        <div class="stat-label">歌曲</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_artists }}</div>
        <div class="stat-label">歌手</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_albums }}</div>
        <div class="stat-label">专辑</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_duration_hours }}h</div>
        <div class="stat-label">总时长</div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <div class="tab" :class="{ active: tab === 'songs' }" @click="tab = 'songs'">全部歌曲</div>
      <div class="tab" :class="{ active: tab === 'artists' }" @click="$router.push('/library/artists')">歌手</div>
      <div class="tab" :class="{ active: tab === 'albums' }" @click="$router.push('/library/albums')">专辑</div>
    </div>

    <!-- Song List -->
    <div class="song-list">
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="songs.length === 0" class="empty-state">
        <div class="empty-icon">🎵</div>
        <div class="empty-text">暂无歌曲，点击下方按钮扫描</div>
      </div>
      <div
        v-for="song in songs"
        :key="song.id"
        class="song-item"
        @click="playSong(song)"
      >
        <img
          v-if="song.cover_url"
          :src="song.cover_url"
          class="song-cover-small"
          alt=""
        />
        <div v-else class="song-cover-small song-cover-small-placeholder">🎵</div>
        <div class="song-info">
          <div class="song-title">{{ song.title }}</div>
          <div class="song-meta">
            {{ song.artist_name }}
            <span v-if="song.album_title"> · {{ song.album_title }}</span>
          </div>
        </div>
        <div class="song-duration">{{ formatTime(song.duration) }}</div>
      </div>
    </div>

    <!-- Scan button -->
    <div style="padding: 16px; text-align: center;">
      <button class="btn btn-primary" @click="scanLibrary" :disabled="scanning">
        {{ scanning ? '扫描中...' : '🔄 扫描音乐库' }}
      </button>
      <button class="btn btn-secondary" style="margin-left: 8px;" @click="fillMetadata" :disabled="filling">
        {{ filling ? '处理中...' : '📝 补全元数据' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { usePlayerStore } from '../stores/player'

const playerStore = usePlayerStore()
const songs = ref([])
const stats = ref(null)
const loading = ref(true)
const scanning = ref(false)
const filling = ref(false)
const searchQuery = ref('')
const tab = ref('songs')

let searchTimeout = null

function formatTime(seconds) {
  if (!seconds) return ''
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

async function loadSongs(query = '') {
  loading.value = true
  try {
    const url = query
      ? `/api/songs/?search=${encodeURIComponent(query)}&page_size=100`
      : '/api/songs/?page_size=100'
    const resp = await fetch(url)
    songs.value = await resp.json()
  } catch (err) {
    console.error('Failed to load songs:', err)
  }
  loading.value = false
}

async function loadStats() {
  try {
    const resp = await fetch('/api/library/stats')
    stats.value = await resp.json()
  } catch (err) {
    console.error('Failed to load stats:', err)
  }
}

function debouncedSearch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => loadSongs(searchQuery.value), 300)
}

function playSong(song) {
  playerStore.setPlaylist(songs.value, songs.value.indexOf(song))
}

async function scanLibrary() {
  scanning.value = true
  try {
    await fetch('/api/library/scan', { method: 'POST' })
    // Wait a bit and reload
    setTimeout(async () => {
      await loadSongs()
      await loadStats()
      scanning.value = false
    }, 3000)
  } catch (err) {
    console.error('Scan failed:', err)
    scanning.value = false
  }
}

async function fillMetadata() {
  filling.value = true
  try {
    await fetch('/api/library/metadata/fill', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
    setTimeout(() => { filling.value = false }, 5000)
  } catch (err) {
    console.error('Metadata fill failed:', err)
    filling.value = false
  }
}

onMounted(() => {
  loadSongs()
  loadStats()
})
</script>
