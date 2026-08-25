import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const usePlayerStore = defineStore('player', () => {
  const currentSong = ref(null)
  const isPlaying = ref(false)
  const currentTime = ref(0)
  const duration = ref(0)
  const volume = ref(0.8)
  const playlist = ref([])
  const currentIndex = ref(-1)
  const audio = ref(null)
  const bitrate = ref(192)
  const lyrics = ref([])
  const currentLyricIndex = ref(-1)

  const progress = computed(() => {
    if (!duration.value) return 0
    return (currentTime.value / duration.value) * 100
  })

  function initAudio() {
    if (audio.value) return

    audio.value = new Audio()
    audio.value.volume = volume.value

    audio.value.addEventListener('timeupdate', () => {
      currentTime.value = audio.value.currentTime
      updateLyricIndex()
    })

    audio.value.addEventListener('loadedmetadata', () => {
      duration.value = audio.value.duration
    })

    audio.value.addEventListener('ended', () => {
      updateMediaSession()
      next()
    })

    audio.value.addEventListener('error', (e) => {
      console.error('Audio error:', e)
      isPlaying.value = false
      updateMediaSession()
    })

    setupMediaSession()

    // Keyboard fallback for car browsers that map hardware keys to key events
    window.addEventListener('keydown', onMediaKey)
  }

  function setupMediaSession() {
    if (!('mediaSession' in navigator)) return
    try {
      navigator.mediaSession.setActionHandler('play', () => {
        if (!isPlaying.value) togglePlay()
      })
      navigator.mediaSession.setActionHandler('pause', () => {
        if (isPlaying.value) togglePlay()
      })
      navigator.mediaSession.setActionHandler('previoustrack', () => prev())
      navigator.mediaSession.setActionHandler('nexttrack', () => next())
      navigator.mediaSession.setActionHandler('seekto', (details) => {
        if (details.seekTime != null) seek(details.seekTime)
      })
    } catch (e) {
      // Media Session not fully supported — keyboard fallback still active
    }
  }

  function updateMediaSession() {
    if (!('mediaSession' in navigator)) return
    try {
      const song = currentSong.value
      if (song) {
        const meta = {
          title: song.title,
          artist: song.artist_name || '',
          album: song.album_title || '',
        }
        if (song.cover_url) {
          meta.artwork = [{ src: song.cover_url, sizes: '512x512' }]
        }
        navigator.mediaSession.metadata = new MediaMetadata(meta)
      }
      navigator.mediaSession.playbackState = isPlaying.value ? 'playing' : 'paused'
    } catch (e) {
      // not supported
    }
  }

  function isEditableTarget(e) {
    const t = e.target
    return t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)
  }

  function onMediaKey(e) {
    // Never hijack keys while typing in a search/input field
    if (isEditableTarget(e)) return
    switch (e.key) {
      case 'MediaTrackNext':
        e.preventDefault()
        next()
        break
      case 'MediaTrackPrevious':
        e.preventDefault()
        prev()
        break
      case 'MediaPlayPause':
        e.preventDefault()
        togglePlay()
        break
      case ' ': // spacebar fallback (some car browsers map play/pause to space)
        e.preventDefault()
        togglePlay()
        break
    }
  }

  function playSong(song) {
    initAudio()
    currentSong.value = song
    isPlaying.value = true

    // Build URL
    const url = `/api/stream/${song.id}?bitrate=${bitrate.value}`
    audio.value.src = url
    audio.value.play().catch(() => {})
    updateMediaSession()

    // Fetch lyrics
    fetchLyrics(song.id)

    // Record play
    fetch(`/api/songs/${song.id}/play`, { method: 'POST' })

    // Pre-cache next songs
    fetch(`/api/stream/cache/pre-cache?song_id=${song.id}`, { method: 'POST' })
  }

  function togglePlay() {
    if (!audio.value) return

    if (isPlaying.value) {
      audio.value.pause()
      isPlaying.value = false
    } else {
      audio.value.play().catch(() => {})
      isPlaying.value = true
    }
    updateMediaSession()
  }

  function next() {
    if (playlist.value.length === 0) return
    currentIndex.value = (currentIndex.value + 1) % playlist.value.length
    playSong(playlist.value[currentIndex.value])
  }

  function prev() {
    if (playlist.value.length === 0) return
    currentIndex.value = currentIndex.value > 0
      ? currentIndex.value - 1
      : playlist.value.length - 1
    playSong(playlist.value[currentIndex.value])
  }

  function seek(time) {
    if (audio.value) {
      audio.value.currentTime = time
    }
  }

  function seekPercent(percent) {
    if (audio.value && duration.value) {
      audio.value.currentTime = (percent / 100) * duration.value
    }
  }

  function setVolume(vol) {
    volume.value = vol
    if (audio.value) {
      audio.value.volume = vol
    }
  }

  function setPlaylist(songs, startIndex = 0) {
    playlist.value = songs
    currentIndex.value = startIndex
    if (songs.length > 0) {
      playSong(songs[startIndex])
    }
  }

  async function fetchLyrics(songId) {
    try {
      const resp = await fetch(`/api/lyrics/${songId}`)
      if (resp.ok) {
        const data = await resp.json()
        lyrics.value = parseLRC(data.content)
      } else {
        lyrics.value = []
      }
    } catch {
      lyrics.value = []
    }
  }

  function parseLRC(lrcText) {
    if (!lrcText) return []
    const lines = lrcText.split('\n')
    const result = []

    for (const line of lines) {
      const match = line.match(/\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)/)
      if (match) {
        const minutes = parseInt(match[1])
        const seconds = parseInt(match[2])
        const ms = parseInt(match[3].padEnd(3, '0'))
        const time = minutes * 60 + seconds + ms / 1000
        const text = match[4].trim()
        if (text) {
          result.push({ time, text })
        }
      }
    }

    return result.sort((a, b) => a.time - b.time)
  }

  function updateLyricIndex() {
    if (!lyrics.value.length) return
    const time = currentTime.value

    for (let i = lyrics.value.length - 1; i >= 0; i--) {
      if (time >= lyrics.value[i].time) {
        currentLyricIndex.value = i
        return
      }
    }
    currentLyricIndex.value = 0
  }

  return {
    currentSong,
    isPlaying,
    currentTime,
    duration,
    volume,
    playlist,
    currentIndex,
    bitrate,
    lyrics,
    currentLyricIndex,
    progress,
    playSong,
    togglePlay,
    next,
    prev,
    seek,
    seekPercent,
    setVolume,
    setPlaylist,
  }
})
