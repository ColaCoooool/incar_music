<template>
  <div>
    <div class="view-header">
      <div class="view-title">歌单</div>
    </div>

    <div class="settings-group">
      <div class="settings-group-title">我的歌单</div>

      <div v-if="playlists.length" class="song-list">
        <div
          v-for="pl in playlists"
          :key="pl.id"
          class="song-item"
          @click="openPlaylist(pl)"
        >
          <div class="song-cover-small song-cover-small-placeholder">📋</div>
          <div class="song-info">
            <div class="song-title">{{ pl.name }}</div>
            <div class="song-meta">{{ pl.song_count || 0 }} 首歌</div>
          </div>
        </div>
      </div>

      <div v-else class="empty-state" style="padding: 40px 20px;">
        <div class="empty-icon">📋</div>
        <div class="empty-text">暂无歌单</div>
      </div>
    </div>

    <!-- Quick playlists -->
    <div class="settings-group">
      <div class="settings-group-title">快速播放</div>
      <div class="song-item" @click="playRecent">
        <div class="song-cover-small song-cover-small-placeholder">🕐</div>
        <div class="song-info">
          <div class="song-title">最近播放</div>
          <div class="song-meta">按播放时间排序</div>
        </div>
      </div>
      <div class="song-item" @click="playMostPlayed">
        <div class="song-cover-small song-cover-small-placeholder">🔥</div>
        <div class="song-info">
          <div class="song-title">最常播放</div>
          <div class="song-meta">按播放次数排序</div>
        </div>
      </div>
      <div class="song-item" @click="playRandom">
        <div class="song-cover-small song-cover-small-placeholder">🎲</div>
        <div class="song-info">
          <div class="song-title">随机播放</div>
          <div class="song-meta">随机播放所有歌曲</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { usePlayerStore } from '../stores/player'

const playerStore = usePlayerStore()
const playlists = ref([])

async function loadPlaylists() {
  // TODO: Add playlists API
  playlists.value = []
}

async function playRecent() {
  const resp = await fetch('/api/songs/?page_size=50&sort_by=date_added&sort_order=desc')
  const songs = await resp.json()
  if (songs.length) playerStore.setPlaylist(songs, 0)
}

async function playMostPlayed() {
  const resp = await fetch('/api/songs/?page_size=50&sort_by=play_count&sort_order=desc')
  const songs = await resp.json()
  if (songs.length) playerStore.setPlaylist(songs, 0)
}

async function playRandom() {
  const resp = await fetch('/api/songs/?page_size=100')
  const songs = await resp.json()
  for (let i = songs.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [songs[i], songs[j]] = [songs[j], songs[i]]
  }
  if (songs.length) playerStore.setPlaylist(songs, 0)
}

function openPlaylist(pl) {
  // TODO: Show playlist songs
}

onMounted(() => loadPlaylists())
</script>
