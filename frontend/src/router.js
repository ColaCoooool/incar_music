import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Player',
    component: () => import('./views/Player.vue'),
  },
  {
    path: '/library',
    name: 'Library',
    component: () => import('./views/Library.vue'),
  },
  {
    path: '/library/artists',
    name: 'Artists',
    component: () => import('./views/Artists.vue'),
  },
  {
    path: '/library/albums',
    name: 'Albums',
    component: () => import('./views/Albums.vue'),
  },
  {
    path: '/playlists',
    name: 'Playlists',
    component: () => import('./views/Playlists.vue'),
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('./views/Settings.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
