<template>
  <div>
    <div class="view-header">
      <div class="view-title">专辑</div>
      <div class="search-bar">
        <span class="search-icon">🔍</span>
        <input v-model="searchQuery" type="text" placeholder="搜索专辑..." @input="debouncedSearch" />
      </div>
    </div>

    <div class="grid" v-if="albums.length">
      <div
        v-for="album in albums"
        :key="album.id"
        class="grid-item"
        @click="viewAlbum(album)"
      >
        <div class="grid-cover-placeholder">💿</div>
        <div class="grid-title">{{ album.title }}</div>
        <div class="grid-subtitle">
          {{ album.artist_name }}
          <span v-if="album.year"> · {{ album.year }}</span>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <div class="empty-icon">💿</div>
      <div class="empty-text">暂无专辑数据</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const albums = ref([])
const searchQuery = ref('')
let searchTimeout = null

async function loadAlbums(query = '') {
  const url = query
    ? `/api/library/albums?search=${encodeURIComponent(query)}`
    : '/api/library/albums'
  const resp = await fetch(url)
  albums.value = await resp.json()
}

function debouncedSearch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => loadAlbums(searchQuery.value), 300)
}

function viewAlbum(album) {
  // TODO: Show album songs
}

onMounted(() => loadAlbums())
</script>
