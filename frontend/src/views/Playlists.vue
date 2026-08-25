<template>
  <div>
    <div class="view-header">
      <div class="view-title">{{ editingPlaylist ? '歌单详情' : '歌单' }}</div>
    </div>

    <!-- Detail view -->
    <template v-if="editingPlaylist">
      <button class="btn btn-secondary" style="margin: 0 4px 8px;" @click="backToList">�?返回</button>
      <div class="settings-group">
        <div class="settings-group-title">{{ editingPlaylist.name }}（{{ editingPlaylist.song_count }} 首）</div>
        <div v-if="playlistSongs.length" class="song-list">
          <div v-for="song in playlistSongs" :key="song.id" class="song-item" @click="playFromPlaylist(song)">
            <div class="song-cover-small song-cover-small-placeholder">🎵</div>
            <div class="song-info">
              <div class="song-title">{{ song.title }}</div>
              <div class="song-meta">{{ song.artist_name }}</div>
            </div>
            <button class="btn btn-secondary"  @click.stop="removeSong(song.id)">移除</button>
          </div>
        </div>
        <div v-else class="empty-state" style="padding: 24px;">歌单为空</div>
      </div>
    </template>

    <!-- List view -->
    <template v-else>
      <div class="settings-group">
        <div class="settings-group-title">创建歌单</div>
        <div style="display: flex; gap: 8px; padding: 0 4px;">
          <input
            v-model="newName"
            type="text"
            placeholder="歌单名称..."
            style="flex: 1; padding: 10px; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); color: var(--text-primary); font-size: 14px; outline: none;"
            @keyup.enter="createPlaylist"
          />
          <button class="btn btn-primary" :disabled="!newName.trim()" @click="createPlaylist">创建</button>
        </div>
      </div>

      <div class="settings-group">
        <div class="settings-group-title">我的歌单</div>
        <div v-if="playlists.length" class="song-list">
          <div v-for="pl in playlists" :key="pl.id" class="song-item" @click="openPlaylist(pl)">
            <div class="song-cover-small song-cover-small-placeholder">📋</div>
            <div class="song-info">
              <div class="song-title">{{ pl.name }}</div>
              <div class="song-meta">{{ pl.song_count }} 首歌</div>
            </div>
            <button class="btn btn-secondary"  @click.stop="renamePlaylist(pl)">改名</button>
            <button class="btn btn-secondary" style="margin-left: 4px;" @click.stop="deletePlaylist(pl)">删除</button>
          </div>
        </div>
        <div v-else class="empty-state" style="padding: 40px 20px;">
          <div class="empty-icon">📋</div>
          <div class="empty-text">暂无歌单，先创建一个吧</div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { usePlayerStore } from '../stores/player'

const playerStore = usePlayerStore()
const playlists = ref([])
const playlistSongs = ref([])
const editingPlaylist = ref(null)
const newName = ref('')

async function loadPlaylists() {
  try {
    const resp = await fetch('/api/playlists')
    playlists.value = await resp.json()
  } catch (err) {
    console.error('Failed to load playlists:', err)
  }
}

async function createPlaylist() {
  if (!newName.value.trim()) return
  try {
    await fetch('/api/playlists', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName.value.trim() }),
    })
    newName.value = ''
    await loadPlaylists()
  } catch (err) {
    console.error('Failed to create playlist:', err)
  }
}

async function openPlaylist(pl) {
  try {
    const resp = await fetch(`/api/playlists/${pl.id}`)
    const data = await resp.json()
    editingPlaylist.value = data
    playlistSongs.value = data.songs
  } catch (err) {
    console.error('Failed to open playlist:', err)
  }
}

function backToList() {
  editingPlaylist.value = null
  playlistSongs.value = []
  loadPlaylists()
}

async function renamePlaylist(pl) {
  const name = window.prompt('新名称：', pl.name)
  if (!name || name === pl.name) return
  try {
    await fetch(`/api/playlists/${pl.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    })
    await loadPlaylists()
  } catch (err) {
    console.error('Failed to rename playlist:', err)
  }
}

async function deletePlaylist(pl) {
  if (!window.confirm(`删除歌单�?{pl.name}」？`)) return
  try {
    await fetch(`/api/playlists/${pl.id}`, { method: 'DELETE' })
    await loadPlaylists()
  } catch (err) {
    console.error('Failed to delete playlist:', err)
  }
}

async function removeSong(songId) {
  try {
    await fetch(`/api/playlists/${editingPlaylist.value.id}/songs/${songId}`, { method: 'DELETE' })
    await openPlaylist(editingPlaylist.value)
  } catch (err) {
    console.error('Failed to remove song:', err)
  }
}

function playFromPlaylist(song) {
  playerStore.setPlaylist(playlistSongs.value, playlistSongs.value.indexOf(song))
}

onMounted(loadPlaylists)
</script>
