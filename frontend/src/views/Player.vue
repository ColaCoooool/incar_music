<template>
  <div class="player-view">
    <!-- Cover + Lyrics side by side (wide), stacked (narrow) -->
    <div class="player-main">
      <div v-if="playerStore.currentSong">
        <img
          v-if="playerStore.currentSong.cover_url"
          :src="playerStore.currentSong.cover_url"
          class="player-cover"
          alt="Album Cover"
        />
        <div v-else class="player-cover player-cover-placeholder">🎵</div>
      </div>
      <div v-else class="player-cover player-cover-placeholder">🎵</div>

      <div class="player-info">
        <div class="player-title">
          {{ playerStore.currentSong?.title || '未在播放' }}
        </div>
        <div class="player-artist">
          {{ playerStore.currentSong?.artist_name || '选择一首歌曲开始' }}
        </div>
        <div v-if="playerStore.lyrics.length" class="lyrics-container" ref="lyricsContainer">
          <div
            v-for="(line, index) in playerStore.lyrics"
            :key="index"
            class="lyric-line"
            :class="{ active: index === playerStore.currentLyricIndex }"
          >
            {{ line.text }}
          </div>
        </div>
      </div>
    </div>

    <!-- Control bar -->
    <div class="player-controls">
      <div class="progress-bar" @click="handleSeek">
        <div class="progress-fill" :style="{ width: playerStore.progress + '%' }"></div>
        <div class="progress-thumb" :style="{ left: playerStore.progress + '%' }"></div>
      </div>
      <div class="progress-times">
        <span>{{ formatTime(playerStore.currentTime) }}</span>
        <span>{{ formatTime(playerStore.duration) }}</span>
      </div>
      <div class="player-buttons">
        <button class="control-btn" @click="playerStore.prev">⏮</button>
        <button class="control-btn play" @click="playerStore.togglePlay">
          {{ playerStore.isPlaying ? '⏸' : '▶️' }}
        </button>
        <button class="control-btn" @click="playerStore.next">⏭</button>
      </div>
      <div style="display: flex; gap: 12px; justify-content: center; padding-top: 8px;">
        <button class="btn btn-secondary" @click="shufflePlay">🔀 随机播放</button>
        <button class="btn btn-secondary" @click="loadAllSongs">📋 加载全部</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { usePlayerStore } from '../stores/player'

const playerStore = usePlayerStore()
const lyricsContainer = ref(null)

function formatTime(seconds) {
  if (!seconds || isNaN(seconds)) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function handleSeek(e) {
  const rect = e.currentTarget.getBoundingClientRect()
  const percent = ((e.clientX - rect.left) / rect.width) * 100
  playerStore.seekPercent(percent)
}

async function loadAllSongs() {
  try {
    const resp = await fetch('/api/songs/?page_size=200')
    const songs = await resp.json()
    if (songs.length > 0) {
      playerStore.setPlaylist(songs, 0)
    }
  } catch (err) {
    console.error('Failed to load songs:', err)
  }
}

async function shufflePlay() {
  try {
    const resp = await fetch('/api/songs/?page_size=200&sort_by=play_count&sort_order=desc')
    const songs = await resp.json()
    // Shuffle
    for (let i = songs.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [songs[i], songs[j]] = [songs[j], songs[i]]
    }
    if (songs.length > 0) {
      playerStore.setPlaylist(songs, 0)
    }
  } catch (err) {
    console.error('Failed to load songs:', err)
  }
}

// Auto-scroll lyrics
watch(
  () => playerStore.currentLyricIndex,
  async (index) => {
    if (lyricsContainer.value && index >= 0) {
      await nextTick()
      const lines = lyricsContainer.value.querySelectorAll('.lyric-line')
      if (lines[index]) {
        lines[index].scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }
  }
)
</script>
