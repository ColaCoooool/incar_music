<template>
  <div>
    <div class="view-header">
      <div class="view-title">歌手</div>
      <div class="search-bar">
        <span class="search-icon">🔍</span>
        <input v-model="searchQuery" type="text" placeholder="搜索歌手..." @input="debouncedSearch" />
      </div>
    </div>

    <div class="grid" v-if="artists.length">
      <div
        v-for="artist in artists"
        :key="artist.id"
        class="grid-item"
        @click="viewArtist(artist)"
      >
        <div class="grid-cover-placeholder">🎤</div>
        <div class="grid-title">{{ artist.name }}</div>
        <div class="grid-subtitle">{{ artist.song_count }} 首歌</div>
      </div>
    </div>

    <div v-else class="empty-state">
      <div class="empty-icon">🎤</div>
      <div class="empty-text">暂无歌手数据</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const artists = ref([])
const searchQuery = ref('')
let searchTimeout = null

async function loadArtists(query = '') {
  const url = query
    ? `/api/library/artists?search=${encodeURIComponent(query)}`
    : '/api/library/artists'
  const resp = await fetch(url)
  artists.value = await resp.json()
}

function debouncedSearch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => loadArtists(searchQuery.value), 300)
}

function viewArtist(artist) {
  // TODO: Show artist songs
}

onMounted(() => loadArtists())
</script>
