<template>
  <div class="app">
    <!-- Dock navigation (wide screens) -->
    <nav class="dock-nav">
      <router-link to="/" class="dock-item" :class="{ active: $route.path === '/' }" title="播放">▶</router-link>
      <router-link to="/library" class="dock-item" :class="{ active: $route.path.startsWith('/library') }" title="曲库">▤</router-link>
      <router-link to="/playlists" class="dock-item" :class="{ active: $route.path === '/playlists' }" title="歌单">☰</router-link>
      <router-link to="/settings" class="dock-item" :class="{ active: $route.path === '/settings' }" title="设置">⚙</router-link>
    </nav>

    <!-- Main content -->
    <main class="main-content">
      <router-view />
    </main>

    <!-- Bottom navigation (narrow screens) -->
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

    <!-- Persistent player bar -->
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
      <button class="mini-next-btn" @click.stop="playerStore.next">⏭</button>
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
