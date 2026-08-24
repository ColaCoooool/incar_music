<template>
  <div class="app">
    <!-- Main content -->
    <main class="main-content">
      <router-view />
    </main>

    <!-- Bottom navigation bar -->
    <nav class="bottom-nav">
      <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }">
        <span class="nav-icon">🎵</span>
        <span class="nav-label">播放</span>
      </router-link>
      <router-link to="/library" class="nav-item" :class="{ active: $route.path.startsWith('/library') }">
        <span class="nav-icon">📚</span>
        <span class="nav-label">曲库</span>
      </router-link>
      <router-link to="/playlists" class="nav-item" :class="{ active: $route.path === '/playlists' }">
        <span class="nav-icon">📋</span>
        <span class="nav-label">歌单</span>
      </router-link>
      <router-link to="/settings" class="nav-item" :class="{ active: $route.path === '/settings' }">
        <span class="nav-icon">⚙️</span>
        <span class="nav-label">设置</span>
      </router-link>
    </nav>

    <!-- Mini player bar -->
    <div v-if="playerStore.currentSong" class="mini-player" @click="expandPlayer">
      <div class="mini-player-info">
        <img
          v-if="playerStore.currentSong.cover_url"
          :src="playerStore.currentSong.cover_url"
          class="mini-cover"
          alt=""
        />
        <div v-else class="mini-cover mini-cover-placeholder">🎵</div>
        <div class="mini-text">
          <div class="mini-title">{{ playerStore.currentSong.title }}</div>
          <div class="mini-artist">{{ playerStore.currentSong.artist_name }}</div>
        </div>
      </div>
      <button class="mini-play-btn" @click.stop="playerStore.togglePlay">
        {{ playerStore.isPlaying ? '⏸' : '▶️' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { usePlayerStore } from './stores/player'

const playerStore = usePlayerStore()
const router = useRouter()

function expandPlayer() {
  router.push('/')
}
</script>
