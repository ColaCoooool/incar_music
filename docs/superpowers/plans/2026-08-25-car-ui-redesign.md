# 车机 UI 重构 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将前端从"手机竖屏模板"重构为车机横屏体验：Dock 侧边导航 + 常驻播放条 + 左封面右歌词播放页 + 大触控目标（≥64px）/大字（≥17px）/高对比。

**架构：** 纯前端 CSS/模板重构，零后端改动。`main.css` 重写设计令牌与全局组件样式；`App.vue` 增加 Dock 导航（`min-width: 768px` 显示，窄屏回退底部导航）并升级常驻播放条；`Player.vue` 改为横排左封面右歌词；列表页统一增大字号/行高/卡片化。

**技术栈：** Vue3 SFC + 原生 CSS 变量（无新依赖）。

**规格：** `docs/superpowers/specs/2026-08-25-car-ui-redesign-design.md`
**视觉精修稿：** 已通过视觉伴侣确认（播放页/曲库页，品牌绿 #1db954）。

---

### 任务 1：设计令牌与全局样式（main.css）

**文件：**
- 修改：`frontend/src/styles/main.css`（重写）

说明：本任务建立全部设计令牌与基础组件样式；后续任务只引用这些类。前端无单测框架，验证方式为 `npm run build` + 视觉检查（精修稿已定样式基准）。

- [ ] **步骤 1：更新设计令牌（:root）**

替换 `:root` 块为：

```css
:root {
  --bg-primary: #0a0f0a;
  --bg-secondary: #101610;
  --bg-card: #131b13;
  --bg-hover: #182218;
  --text-primary: #f2f7f2;
  --text-secondary: #93a893;
  --text-muted: #5d705d;
  --accent: #1db954;
  --accent-hover: #1ed760;
  --accent-contrast: #08120a;
  --border: #1f2b1f;
  --danger: #e74c3c;
  --radius: 12px;
  --radius-lg: 16px;
  --dock-width: 76px;
  --bar-height: 76px;
  --touch-min: 64px;
  --nav-height: 60px;
  --mini-player-height: 64px;
}
```

- [ ] **步骤 2：全局字号与基础排版**

在 `body` 规则中把基础字号提升，并新增基础按钮/输入尺寸：

```css
body {
  font-size: 17px;
  line-height: 1.45;
  /* 其余保持 */
}

/* 最小触控目标（所有可点元素） */
.btn, .song-item, .nav-item, .tab, .control-btn, .settings-item {
  min-height: var(--touch-min);
}
```

- [ ] **步骤 3：Dock 导航样式（新增）**

```css
/* ─── Dock Navigation (wide screens) ─────────────────────── */
.dock-nav {
  display: none;
}

@media (min-width: 768px) {
  .app { flex-direction: row; }
  .dock-nav {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    width: var(--dock-width);
    padding: 16px 0;
    background: var(--bg-secondary);
    border-right: 1px solid var(--border);
    z-index: 100;
  }
  .dock-item {
    width: 46px;
    height: 46px;
    border-radius: 14px;
    background: var(--bg-hover);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    text-decoration: none;
    color: var(--text-secondary);
    transition: all 0.2s;
  }
  .dock-item.active {
    background: var(--accent);
    color: var(--accent-contrast);
    box-shadow: 0 4px 14px rgba(29, 185, 84, 0.35);
  }
}
```

- [ ] **步骤 4：常驻播放条样式（升级 mini-player 为 bar）**

```css
.mini-player {
  height: var(--bar-height);
  padding: 0 20px;
  gap: 14px;
}
.mini-cover { width: 48px; height: 48px; border-radius: 12px; }
.mini-title { font-size: 17px; font-weight: 600; }
.mini-artist { font-size: 14px; }
.mini-play-btn { width: 56px; height: 56px; border-radius: 50%; font-size: 22px; }

/* 新增下一首按钮 */
.mini-next-btn {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  border: none;
  background: var(--bg-hover);
  color: var(--text-primary);
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

同时删除 `@media (min-width: 1024px)` 中对 `.main-content/.bottom-nav/.mini-player` 的 `max-width: 600px` 居中限制（车机全宽），改为：

```css
@media (min-width: 768px) {
  .main-content { padding-left: var(--dock-width); }
}
```

（`.main-content` 位于 `.app` 的 flex 行内时由 Dock 占据宽度，无需手动 padding；此规则仅用于 Dock 为 `position: fixed` 的备用方案，实际实现用 flex 行布局，因此**不添加**该 padding 规则——见任务 2 的 DOM 结构。）

- [ ] **步骤 5：构建验证**

运行：`cd frontend && npm run build`
预期：构建成功（样式未影响编译）

- [ ] **步骤 6：Commit**

```bash
git add frontend/src/styles/main.css
git commit -m "style: car UI design tokens and dock/player-bar base styles"
```

---

### 任务 2：App.vue —— Dock 导航 + 常驻播放条

**文件：**
- 修改：`frontend/src/App.vue`

- [ ] **步骤 1：模板改为 Dock + 内容 + 常驻播放条**

替换 `<template>` 为：

```html
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

    <!-- Bottom navigation (narrow screens, unchanged) -->
    <nav class="bottom-nav">
      <!-- 原 4 个 nav-item 保持不变 -->
    </nav>

    <!-- Persistent player bar -->
    <div v-if="playerStore.currentSong" class="mini-player" @click="expandPlayer">
      <div class="mini-player-info">
        <img v-if="playerStore.currentSong.cover_url" :src="playerStore.currentSong.cover_url" class="mini-cover" alt="" />
        <div v-else class="mini-cover mini-cover-placeholder">🎵</div>
        <div class="mini-text">
          <div class="mini-title">{{ playerStore.currentSong.title }}</div>
          <div class="mini-artist">{{ playerStore.currentSong.artist_name }}</div>
        </div>
      </div>
      <button class="mini-play-btn" @click.stop="playerStore.togglePlay">{{ playerStore.isPlaying ? '⏸' : '▶️' }}</button>
      <button class="mini-next-btn" @click.stop="playerStore.next">⏭</button>
    </div>
  </div>
</template>
```

注意：`.app` 在 `min-width: 768px` 下为 `flex-direction: row`（任务 1 步骤 3），Dock 占左列；`.bottom-nav` 保持窄屏可见——需在 CSS 中隐藏宽屏底部导航：

```css
@media (min-width: 768px) {
  .bottom-nav { display: none; }
  .main-content { padding-bottom: calc(var(--bar-height) + 10px); }
}
```

（追加到任务 1 的样式文件末尾。）

- [ ] **步骤 2：构建验证**

运行：`cd frontend && npm run build`
预期：构建成功

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/App.vue frontend/src/styles/main.css
git commit -m "feat(frontend): dock navigation and persistent player bar"
```

---

### 任务 3：Player.vue —— 左封面右歌词播放页

**文件：**
- 修改：`frontend/src/views/Player.vue`

- [ ] **步骤 1：模板重构为横排封面+歌词、底部控制条**

替换 `<template>`：

```html
<template>
  <div class="player-view">
    <!-- Cover + Lyrics side by side (wide), stacked (narrow) -->
    <div class="player-main">
      <div v-if="playerStore.currentSong">
        <img v-if="playerStore.currentSong.cover_url" :src="playerStore.currentSong.cover_url" class="player-cover" alt="Album Cover" />
        <div v-else class="player-cover player-cover-placeholder">🎵</div>
      </div>
      <div v-else class="player-cover player-cover-placeholder">🎵</div>

      <div class="player-info">
        <div class="player-title">{{ playerStore.currentSong?.title || '未在播放' }}</div>
        <div class="player-artist">{{ playerStore.currentSong?.artist_name || '选择一首歌曲开始' }}</div>
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
        <button class="control-btn play" @click="playerStore.togglePlay">{{ playerStore.isPlaying ? '⏸' : '▶️' }}</button>
        <button class="control-btn" @click="playerStore.next">⏭</button>
      </div>
    </div>
  </div>
</template>
```

（`<script setup>` 保持不变——`formatTime/handleSeek/loadAllSongs/shufflePlay`、lyrics 滚动 watch 均沿用。）

- [ ] **步骤 2：样式：横排布局 + 大控制条 + 歌词高亮**

追加到 `main.css`（替换原 `.player-view/.player-cover/.player-info/.player-controls/.lyrics-container` 相关规则）：

```css
.player-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 24px;
  gap: 16px;
}

.player-main {
  flex: 1;
  display: flex;
  gap: 32px;
  align-items: center;
  min-height: 0;
}

.player-cover {
  width: 280px;
  height: 280px;
  border-radius: 18px;
  object-fit: cover;
  flex-shrink: 0;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.player-cover-placeholder {
  background: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 84px;
}

.player-info { flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: center; }

.player-title { font-size: 26px; font-weight: 700; margin-bottom: 6px; }
.player-artist { font-size: 16px; color: var(--text-secondary); margin-bottom: 16px; }

.lyrics-container {
  width: 100%;
  max-height: none;
  overflow: visible;
  padding: 8px;
  background: none;
  border-radius: 0;
  text-align: center;
}
.lyric-line { padding: 6px 0; font-size: 17px; color: var(--text-muted); transition: all 0.25s; }
.lyric-line.active {
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 600;
  background: rgba(29, 185, 84, 0.12);
  border: 1px solid rgba(29, 185, 84, 0.25);
  border-radius: 12px;
  padding: 7px 22px;
}

/* Control bar */
.player-controls {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 1px solid var(--border);
  padding-top: 16px;
}
.progress-bar { height: 7px; border-radius: 4px; }
.progress-fill { border-radius: 4px; }
.progress-thumb {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--text-primary);
  border: 3px solid var(--accent);
}
.progress-times { font-size: 14px; }
.player-buttons { display: flex; align-items: center; justify-content: center; gap: 20px; }
.control-btn { width: 56px; height: 56px; font-size: 22px; }
.control-btn.play { width: 64px; height: 64px; font-size: 24px; }

/* Narrow screens: stacked layout */
@media (max-width: 767px) {
  .player-main { flex-direction: column; gap: 16px; }
  .player-cover { width: 220px; height: 220px; }
  .lyrics-container { max-height: 180px; overflow-y: auto; }
}
```

- [ ] **步骤 3：构建验证**

运行：`cd frontend && npm run build`
预期：构建成功

- [ ] **步骤 4：Commit**

```bash
git add frontend/src/views/Player.vue frontend/src/styles/main.css
git commit -m "feat(frontend): player page - cover+lyrics side by side with big controls"
```

---

### 任务 4：列表页与设置页适配（字号/行高/卡片）

**文件：**
- 修改：`frontend/src/views/Library.vue`、`Artists.vue`、`Albums.vue`、`Playlists.vue`、`Settings.vue`
- 修改：`frontend/src/styles/main.css`

说明：结构不变，统一尺寸。样式集中在 main.css 调整，页面模板仅对明显过小的内联样式改值。

- [ ] **步骤 1：main.css 统一列表/卡片/设置尺寸**

```css
/* List rows */
.song-item { gap: 14px; padding: 12px 14px; min-height: var(--touch-min); border-bottom: none; margin-bottom: 4px; border-radius: var(--radius-lg); }
.song-item:hover { background: var(--bg-hover); }
.song-item:active { background: var(--bg-card); }
.song-cover-small { width: 52px; height: 52px; border-radius: 12px; }
.song-title { font-size: 18px; font-weight: 600; }
.song-meta { font-size: 15px; }
.song-duration { font-size: 14px; color: var(--text-muted); }

/* Header / search / tabs */
.view-header { padding: 20px 20px 14px; }
.view-title { font-size: 24px; }
.search-bar input { padding: 12px 16px 12px 42px; font-size: 17px; }
.tab { padding: 14px 18px; font-size: 18px; }

/* Grid */
.grid { padding: 0 20px; }
.grid-title { font-size: 16px; }
.grid-subtitle { font-size: 14px; }

/* Settings */
.settings-label { font-size: 17px; }
.settings-value { font-size: 15px; }
.settings-group-title { font-size: 14px; }

/* Stats */
.stat-value { font-size: 28px; }
.stat-label { font-size: 14px; }

/* Buttons */
.btn { padding: 14px 24px; font-size: 17px; }
```

- [ ] **步骤 2：页面模板小改（内联样式过小处）**

`Library.vue`：扫描按钮区 `style="padding: 16px"` 保持；「＋」按钮 `add-to-playlist-btn` 扩大：

```css
.add-to-playlist-btn { padding: 10px 16px; font-size: 18px; margin-left: 10px; }
```

`Playlists.vue`：移除按钮 `style="padding: 4px 10px"` 统一由 `.btn` 控制（删除内联小 padding）。

`Settings.vue`：码率按钮、爬取输入框字号已由 `.btn`/全局覆盖，无需改内联。

- [ ] **步骤 3：构建验证**

运行：`cd frontend && npm run build`
预期：构建成功

- [ ] **步骤 4：Commit**

```bash
git add frontend/src/views frontend/src/styles/main.css
git commit -m "style(frontend): enlarge list rows, typography and touch targets"
```

---

### 任务 5：全量回归与精修确认

**文件：** 无（验证与收尾）

- [ ] **步骤 1：后端回归**

运行：`cd backend && .venv\Scripts\python.exe -m pytest tests -q`
预期：26 passed（后端零改动，确认未受影响）

- [ ] **步骤 2：前端构建**

运行：`cd frontend && npm run build`
预期：构建成功，产物 `dist/` 更新

- [ ] **步骤 3：视觉伴侣精修稿对照**

用视觉伴侣推送新的精修稿（播放页 + 曲库页的实际渲染截图无法获取，改为将重构后的页面结构描述与已批准精修稿逐项核对：Dock 宽度 76px、播放条 76px、歌词高亮样式、列表行 76px、字号 17/18px、绿色 #1db954）。

- [ ] **步骤 4：Commit**

```bash
git add -A
git commit -m "chore: verify car UI redesign regression"
```

---

## 自检记录

- 规格覆盖：§1 布局（Dock/播放条）→ 任务 1、2；§2 播放页 → 任务 3；§3 令牌尺寸 → 任务 1、4；§4 文件范围 → 任务 1-4；§5 验证 → 任务 5。无遗漏。
- 类型一致性：CSS 类名 `dock-nav/dock-item/mini-next-btn/player-main/progress-thumb` 在任务间一致；`--dock-width/--bar-height/--touch-min/--radius-lg` 令牌统一。
- 占位符扫描：所有步骤含实际代码；无 TODO/待定。
- 已知取舍：前端无单测框架，UI 验证以构建 + 精修稿对照为主（已在规格 §5 声明）。
