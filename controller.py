import argparse
import configparser
import ctypes
import json
import os
import queue
import random
import shutil
import socket
import subprocess
import threading
import time
import unicodedata
import html
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = Path(
    os.environ.get("POKEMON_ANIL_LIVE_CONFIG")
    or os.environ.get("POKEMON_LIVE_CHAOS_CONFIG")
    or ROOT / "config" / "actions_anil.json"
)
MANIFEST_PATH = ROOT / "game-manifest.json"
LOG_PATH = ROOT / "logs" / "events.jsonl"
LUA_RESULT_PATH = ROOT / "logs" / "lua_socket_events.jsonl"
MGBA_CONFIG_PATH = Path.home() / "AppData" / "Roaming" / "mGBA" / "config.ini"
PORTABLE_MGBA_CONFIG_PATH = ROOT / "config" / "mgba_config.ini"
TEAM_OVERLAY_ROOT = Path(os.environ.get("APPDATA", "")) / "Pokemon Anil Live" / "team_overlay"
TEAM_JSON_PATH = TEAM_OVERLAY_ROOT / "team.json"
TEAM_SPRITE_DIR = TEAM_OVERLAY_ROOT / "team_sprites"
GAME_UI_ROOT = ROOT / "POKEMON_ANIL" / "Pokemon Anil" / "Graphics" / "UI"
PARTY_UI_DIR = GAME_UI_ROOT / "Bag Screen with Party"

ACTION_QUEUE = queue.Queue()
QUEUE_LOCK = threading.Lock()
QUEUED_EVENT_IDS = set()
PROCESSED_EVENT_IDS = set()
RECENT_QUEUE_RESULTS = []
WORKER_STARTED = False
SAVE_MONITOR_STARTED = False
SAVE_MONITOR_STATE = {}


PANEL_HTML = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Pokemon Anil Live</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #101214;
      --panel: #171b20;
      --panel-2: #1f252b;
      --line: #303842;
      --muted: #9ca8b4;
      --text: #f3f6f8;
      --green: #58c58b;
      --blue: #6aa9ff;
      --red: #e16f6f;
      --amber: #dfb45f;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, Segoe UI, Arial, sans-serif;
    }
    main {
      width: min(1180px, calc(100vw - 28px));
      margin: 0 auto;
      padding: 18px 0 24px;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 10px 0 16px;
      border-bottom: 1px solid var(--line);
    }
    h1 { margin: 0; font-size: 22px; font-weight: 750; }
    h2 { margin: 0 0 10px; font-size: 14px; font-weight: 700; color: #dbe4ea; }
    code { color: #dbe4ea; }
    .mode {
      display: inline-flex;
      gap: 7px;
      align-items: center;
      min-height: 34px;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 0 12px;
      background: #14181c;
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }
    .dot { width: 8px; height: 8px; border-radius: 99px; background: var(--green); box-shadow: 0 0 12px rgba(88,197,139,.55); }
    .statusbar {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin: 16px 0;
    }
    .stat {
      min-height: 74px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: var(--panel);
    }
    .stat strong { display: block; color: var(--muted); font-size: 12px; font-weight: 650; margin-bottom: 8px; }
    .stat span { display: block; font-size: 22px; font-weight: 760; line-height: 1.1; }
    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1.55fr) minmax(320px, .95fr);
      gap: 14px;
      align-items: start;
    }
    .stack { display: grid; gap: 14px; }
    section {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 14px;
    }
    .actions {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }
    button {
      min-height: 54px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel-2);
      color: var(--text);
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      transition: border-color .12s ease, background .12s ease, transform .12s ease;
    }
    button:hover { border-color: #536171; background: #252c33; }
    button:active { transform: translateY(1px); }
    button.good { border-color: rgba(88,197,139,.65); }
    button.good:hover { background: #1e3029; }
    button.bad { border-color: rgba(225,111,111,.7); }
    button.bad:hover { background: #332426; }
    button.blue { border-color: rgba(106,169,255,.7); }
    button.blue:hover { background: #202c3b; }
    button.amber { border-color: rgba(223,180,95,.75); }
    button.amber:hover { background: #312c20; }
    .batch {
      display: grid;
      grid-template-columns: minmax(170px, 1fr) 96px 150px;
      gap: 10px;
    }
    select, input {
      width: 100%;
      min-height: 48px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #111519;
      color: var(--text);
      font-size: 14px;
      padding: 0 11px;
    }
    .console {
      min-height: 180px;
      max-height: 220px;
      overflow: auto;
      white-space: pre-wrap;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #0b0e11;
      color: #d9e2e8;
      padding: 12px;
      font-size: 12px;
      line-height: 1.45;
    }
    .recent {
      display: grid;
      gap: 8px;
      min-height: 132px;
    }
    .event-row {
      display: grid;
      grid-template-columns: 52px minmax(0, 1fr);
      gap: 10px;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px 10px;
      background: #14181c;
      font-size: 13px;
    }
    .pill {
      text-align: center;
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 11px;
      font-weight: 800;
      color: #08110d;
      background: var(--green);
    }
    .pill.err { background: var(--red); color: #190808; }
    .event-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .event-sub { color: var(--muted); margin-top: 2px; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .raw-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }
    .raw-grid button { min-height: 44px; font-size: 13px; }
    .game-log {
      min-height: 170px;
      max-height: 240px;
      border-color: rgba(88,197,139,.45);
    }
    .confirm-strip {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 10px;
      align-items: center;
      margin-bottom: 10px;
      border: 1px solid rgba(88,197,139,.45);
      border-radius: 8px;
      background: #102019;
      padding: 10px 12px;
    }
    .confirm-strip strong { display: block; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .confirm-strip span { display: block; margin-top: 3px; color: var(--muted); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .confirm-badge { color: #08110d; background: var(--green); border-radius: 999px; padding: 5px 9px; font-size: 11px; font-weight: 850; }
    @media (max-width: 920px) {
      .layout { grid-template-columns: 1fr; }
      .statusbar { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 620px) {
      main { width: min(100vw - 20px, 1180px); }
      header { align-items: flex-start; flex-direction: column; }
      .statusbar, .actions, .batch, .raw-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Pokemon Anil Live</h1>
      <div class="mode"><span class="dot"></span><span id="modeText">Anil Live</span></div>
    </header>

    <div class="statusbar">
      <div class="stat"><strong>Cola</strong><span id="queueSize">...</span></div>
      <div class="stat"><strong>Procesados</strong><span id="processedCount">...</span></div>
      <div class="stat"><strong>Ultimo evento</strong><span id="lastStatus">...</span></div>
      <div class="stat"><strong>Botones</strong><span id="keySummary">...</span></div>
    </div>

    <div class="layout">
      <div class="stack">
        <section>
          <h2>Directo</h2>
          <div class="actions">
            <button class="good" onclick="runAction('add_potion_live')">+1 Pocion</button>
            <button class="good" onclick="runAction('add_revive_live')">+1 Revivir</button>
            <button class="good" onclick="runAction('add_pokeball_live')">+1 Poke Ball</button>
            <button class="blue" onclick="runAction('heal_party_live')">Curar Equipo</button>
          </div>
        </section>

        <section>
          <h2>Confirmacion Anil</h2>
          <div class="confirm-strip">
            <div>
              <strong id="gameConfirmTitle">Esperando evento</strong>
              <span id="gameConfirmSub">Cuando el juego aplique algo, aparece aqui.</span>
            </div>
            <div class="confirm-badge" id="gameConfirmBadge">LIVE</div>
          </div>
          <pre id="gameLog" class="console game-log">Cargando confirmacion del juego...</pre>
        </section>

        <section>
          <h2>Cantidad</h2>
          <div class="batch">
            <select id="batchAction">
              <option value="add_potion_live">Pociones</option>
              <option value="add_revive_live">Revivir</option>
              <option value="add_pokeball_live">Poke Balls</option>
              <option value="heal_party_live">Curar equipo</option>
              <option value="mash_a">Mash A</option>
              <option value="chaos_walk">Caminar caos</option>
              <option value="spin_walk">Girar</option>
              <option value="panic_mode">Panico</option>
            </select>
            <input id="batchCount" type="number" min="1" max="250" value="10" />
            <button class="good" onclick="runBatch()">Enviar</button>
          </div>
        </section>

        <section>
          <h2>Caos</h2>
          <div class="actions">
            <button class="amber" onclick="runAction('tap_a')">A</button>
            <button class="amber" onclick="runAction('press_b')">B</button>
            <button class="amber" onclick="runAction('open_menu')">Menu</button>
            <button class="bad" onclick="runAction('chaos_walk')">Caminar</button>
            <button class="bad" onclick="runAction('spin_walk')">Girar</button>
            <button class="bad" onclick="runAction('panic_mode')">Panico</button>
            <button class="bad" onclick="runAction('mash_a')">Mash A</button>
            <button class="amber" onclick="runAction('panic_select')">Select</button>
          </div>
        </section>
      </div>

      <div class="stack">
        <section>
          <h2>Actividad</h2>
          <div id="recent" class="recent"></div>
        </section>

        <section>
          <h2>Respuesta</h2>
          <pre id="log" class="console">Listo.</pre>
        </section>

        <section>
          <h2>Teclas</h2>
          <div class="raw-grid">
            <button onclick="runRawKey('c')">C</button>
            <button onclick="runRawKey('x')">X</button>
            <button onclick="runRawKey('z')">Z</button>
            <button onclick="runRawKey('enter')">Enter</button>
            <button onclick="runRawKey('shift')">Shift</button>
            <button onclick="runRawKey('backspace')">Backspace</button>
            <button onclick="runRawKey('up')">Arriba</button>
            <button onclick="runRawKey('down')">Abajo</button>
            <button onclick="runRawKey('left')">Izquierda</button>
            <button onclick="runRawKey('right')">Derecha</button>
          </div>
        </section>

        <section>
          <h2>Estado</h2>
          <pre id="queue" class="console">Cargando cola...</pre>
        </section>
      </div>
    </div>
  </main>
  <script>
    const log = document.getElementById('log');
    const recentBox = document.getElementById('recent');

    function setLog(payload) {
      log.textContent = typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2);
    }

    async function postJson(path, body) {
      const response = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      return response.json();
    }

    async function runAction(action) {
      const eventId = `${action}-${Date.now()}`;
      setLog(`Enviando ${action}...`);
      try {
        const payload = await postJson('/event', { event_id: eventId, action });
        setLog(payload);
        loadQueue();
      } catch (error) {
        setLog(String(error && error.message ? error.message : error));
      }
    }

    async function runRawKey(rawKey) {
      const eventId = `raw-${rawKey}-${Date.now()}`;
      setLog(`Enviando tecla ${rawKey}...`);
      try {
        const payload = await postJson('/event', { event_id: eventId, raw_key: rawKey });
        setLog(payload);
        loadQueue();
      } catch (error) {
        setLog(String(error && error.message ? error.message : error));
      }
    }

    async function runBatch() {
      const action = document.getElementById('batchAction').value;
      const count = Number(document.getElementById('batchCount').value || 1);
      setLog(`Enviando ${count} x ${action}...`);
      try {
        const payload = await postJson('/batch', { action, count });
        setLog(payload);
        loadQueue();
      } catch (error) {
        setLog(String(error && error.message ? error.message : error));
      }
    }

    async function loadKeys() {
      try {
        const response = await fetch('/api/keys');
        const payload = await response.json();
        const keys = payload.keys || {};
        document.getElementById('keySummary').textContent = `A ${keys.a || '?'} / B ${keys.b || '?'} / Start ${keys.start || '?'}`;
      } catch (_error) {
        document.getElementById('keySummary').textContent = 'error';
      }
    }

    function renderRecent(recent) {
      const items = recent.slice(-6).reverse();
      if (!items.length) {
        recentBox.innerHTML = '<div class="event-row"><span class="pill">OK</span><div><div class="event-title">Sin eventos recientes</div><div class="event-sub">Esperando actividad</div></div></div>';
        return;
      }
      recentBox.innerHTML = items.map((item) => {
        const result = item.result || {};
        const ok = item.ok !== false && result.ok !== false;
        const title = result.resolved_action || result.action || item.event_id || 'evento';
        const sub = result.error || result.file_command || result.raw_key || item.time || '';
        return `<div class="event-row"><span class="pill ${ok ? '' : 'err'}">${ok ? 'OK' : 'ERR'}</span><div><div class="event-title">${escapeHtml(title)}</div><div class="event-sub">${escapeHtml(sub)}</div></div></div>`;
      }).join('');
    }

    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>"']/g, (ch) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
      }[ch]));
    }

    function renderGameConfirmation(lines) {
      const added = [...lines].reverse().find((line) => line.includes(' added '));
      const queued = [...lines].reverse().find((line) => line.includes(' queued '));
      const title = document.getElementById('gameConfirmTitle');
      const sub = document.getElementById('gameConfirmSub');
      const badge = document.getElementById('gameConfirmBadge');
      if (added) {
        title.textContent = added.replace(/^\\S+\\s+\\S+\\s+/, '');
        sub.textContent = 'Confirmado por Pokemon Anil';
        badge.textContent = 'OK';
        badge.style.background = 'var(--green)';
      } else if (queued) {
        title.textContent = queued.replace(/^\\S+\\s+\\S+\\s+/, '');
        sub.textContent = 'En cola dentro del juego';
        badge.textContent = 'COLA';
        badge.style.background = 'var(--amber)';
      } else {
        title.textContent = 'Esperando evento';
        sub.textContent = 'Cuando el juego aplique algo, aparece aqui.';
        badge.textContent = 'LIVE';
        badge.style.background = 'var(--green)';
      }
    }

    async function loadQueue() {
      try {
        const response = await fetch('/api/queue');
        const payload = await response.json();
        document.getElementById('queue').textContent = JSON.stringify(payload, null, 2);
        document.getElementById('queueSize').textContent = String(payload.queue_size ?? '?');
        document.getElementById('processedCount').textContent = String(payload.processed_event_ids ?? '?');
        const recent = payload.recent || [];
        const last = recent.length ? recent[recent.length - 1] : null;
        document.getElementById('lastStatus').textContent = last ? (last.ok ? 'OK' : 'ERROR') : '...';
        renderRecent(recent);
      } catch (error) {
        document.getElementById('queue').textContent = String(error && error.message ? error.message : error);
        document.getElementById('queueSize').textContent = 'error';
        document.getElementById('lastStatus').textContent = 'error';
      }
    }

    async function loadGameLog() {
      try {
        const response = await fetch('/api/live-log');
        const payload = await response.json();
        const lines = payload.lines || [];
        document.getElementById('gameLog').textContent = lines.length
          ? lines.join('\\n')
          : 'Sin confirmaciones del juego todavia.';
        renderGameConfirmation(lines);
      } catch (error) {
        document.getElementById('gameLog').textContent = String(error && error.message ? error.message : error);
      }
    }

    loadKeys();
    loadQueue();
    loadGameLog();
    setInterval(loadQueue, 1000);
    setInterval(loadGameLog, 1000);
  </script>
</body>
</html>
"""

TEAM_OVERLAY_HTML = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Pokemon Anil Live Team Overlay</title>
  <style>
    * { box-sizing: border-box; }
    html, body {
      width: 100%;
      height: 100%;
      margin: 0;
      overflow: hidden;
      background: transparent;
    }
    body {
      display: grid;
      place-items: center;
      font-family: "Arial Black", Impact, Arial, sans-serif;
    }
    .party {
      width: min(440px, 100vw);
      aspect-ratio: 440 / 600;
      position: relative;
      background: transparent;
      transform-origin: center;
    }
    .slot {
      position: absolute;
      width: 50%;
      height: 33.3333%;
      background-image: url('/party-ui/ptpanel_rect_desel.png');
      background-size: 100% 100%;
      background-repeat: no-repeat;
      image-rendering: pixelated;
      overflow: visible;
      color: #f8f8f8;
      text-shadow: 2px 2px 0 #080808, -1px -1px 0 #080808, 1px -1px 0 #080808, -1px 1px 0 #080808;
    }
    .slot.empty {
      background-image: url('/party-ui/ptpanel_blank.png');
      opacity: .88;
    }
    .slot.fainted { background-image: url('/party-ui/ptpanel_rect_faint.png'); }
    .slot:nth-child(1) { left: 0; top: 0; }
    .slot:nth-child(2) { left: 50%; top: 0; }
    .slot:nth-child(3) { left: 0; top: 33.3333%; }
    .slot:nth-child(4) { left: 50%; top: 33.3333%; }
    .slot:nth-child(5) { left: 0; top: 66.6666%; }
    .slot:nth-child(6) { left: 50%; top: 66.6666%; }
    .sprite-frame {
      position: absolute;
      left: 0;
      top: 0;
      width: 128px;
      height: 128px;
      overflow: hidden;
      z-index: 3;
    }
    .sprite-frame img {
      position: absolute;
      left: 0;
      top: 0;
      width: 256px;
      height: 128px;
      image-rendering: pixelated;
      object-fit: none;
    }
    .level {
      position: absolute;
      left: 68px;
      top: 20px;
      display: flex;
      align-items: flex-end;
      gap: 1px;
      line-height: 1;
      z-index: 4;
    }
    .lv-label {
      color: #e4d33f;
      font-size: 28px;
      letter-spacing: 0;
    }
    .lv-number {
      color: white;
      font-size: 52px;
      letter-spacing: 0;
      transform: translateY(2px);
    }
    .gender {
      position: absolute;
      right: 24px;
      top: 44px;
      font-size: 42px;
      line-height: 1;
      z-index: 4;
    }
    .gender.male { color: #52a7ff; }
    .gender.female { color: #ff73c8; }
    .shiny-star {
      position: absolute;
      right: 38px;
      top: 88px;
      width: 28px;
      height: 32px;
      color: #ff0f22;
      font-size: 42px;
      line-height: 24px;
      transform: rotate(45deg);
      z-index: 4;
    }
    .hpbar {
      position: absolute;
      left: 12px;
      top: 120px;
      width: 196px;
      height: 24px;
      background-image: url('/party-ui/overlay_hp_back.png');
      background-size: 100% 100%;
      background-repeat: no-repeat;
      padding: 6px 8px 6px 8px;
      z-index: 5;
    }
    .slot.fainted .hpbar { background-image: url('/party-ui/overlay_hp_back.png'); }
    .hpfill {
      height: 100%;
      width: 0%;
      background: #39ef44;
      box-shadow: inset 0 -1px 0 rgba(0,0,0,.28);
    }
    .hpfill.mid { background: #f6d338; }
    .hpfill.low { background: #e83b31; }
    .hptext {
      position: absolute;
      left: 0;
      top: 148px;
      width: 220px;
      text-align: center;
      font-size: 54px;
      line-height: 1;
      letter-spacing: 0;
      z-index: 6;
    }
    .offline {
      position: absolute;
      left: 0;
      right: 0;
      bottom: -34px;
      color: white;
      background: rgba(0,0,0,.74);
      border: 2px solid rgba(255,255,255,.8);
      padding: 6px 10px;
      font: 700 14px Arial, sans-serif;
      display: none;
      text-shadow: none;
    }
    .offline.show { display: block; }
    @media (min-width: 441px) {
      .party { width: 440px; height: 600px; }
    }
  </style>
</head>
<body>
  <main class="party" id="team"></main>
  <script>
    const teamEl = document.getElementById('team');
    const emptyTeam = Array.from({ length: 6 }, (_, i) => ({ slot: i + 1, empty: true, hp: 0, totalhp: 0 }));

    function pct(mon) {
      const hp = Number(mon.hp || 0);
      const total = Math.max(1, Number(mon.totalhp || 0));
      return Math.max(0, Math.min(100, Math.round((hp / total) * 100)));
    }
    function clean(value) {
      return String(value || '').replace(/[<>&]/g, '');
    }
    function genderMark(mon) {
      if (mon.gender === 'male') return '<span class="gender male">?</span>';
      if (mon.gender === 'female') return '<span class="gender female">?</span>';
      return '';
    }
    function render(team, offlineText = '') {
      const sorted = [...emptyTeam];
      for (const mon of team || []) {
        const slot = Number(mon.slot || 0);
        if (slot >= 1 && slot <= 6) sorted[slot - 1] = mon;
      }
      const now = Date.now();
      teamEl.innerHTML = sorted.map((mon, index) => {
        const empty = !!mon.empty;
        const value = pct(mon);
        const hpClass = value <= 25 ? 'low' : value <= 50 ? 'mid' : '';
        const fainted = !empty && (!!mon.fainted || Number(mon.hp || 0) <= 0);
        const sprite = mon.sprite || `/team-sprite/${index + 1}.png`;
        return `
          <section class="slot ${empty ? 'empty' : ''} ${fainted ? 'fainted' : ''}">
            ${empty ? '' : `<div class="sprite-frame"><img src="${sprite}?t=${now}" alt=""></div>`}
            ${empty ? '' : `<div class="level"><span class="lv-label">Nv.</span><span class="lv-number">${clean(mon.level || 0)}</span></div>`}
            ${empty ? '' : genderMark(mon)}
            ${!empty && mon.shiny ? '<div class="shiny-star">?</div>' : ''}
            ${empty ? '' : `<div class="hpbar"><div class="hpfill ${hpClass}" style="width:${value}%"></div></div>`}
            ${empty ? '' : `<div class="hptext">${clean(mon.hp || 0)} / ${clean(mon.totalhp || 0)}</div>`}
          </section>`;
      }).join('') + `<div class="offline ${offlineText ? 'show' : ''}">${clean(offlineText)}</div>`;
    }
    async function refresh() {
      try {
        const response = await fetch('/team.json?t=' + Date.now(), { cache: 'no-store' });
        const payload = await response.json();
        if (!payload.ok) throw new Error(payload.error || 'bad team payload');
        render(payload.team || []);
      } catch (error) {
        render([], error.message === 'team_not_ready'
          ? 'Abre una partida en Pokemon Anil Live'
          : 'Pokemon Anil Live desconectado');
      }
    }
    render([]);
    refresh();
    setInterval(refresh, 1000);
  </script>
</body>
</html>
"""

TEAM_SLOT_OVERLAY_HTML = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Pokemon Anil Live Slot Overlay</title>
  <style>
    * { box-sizing: border-box; }
    html, body {
      width: 100%;
      height: 100%;
      margin: 0;
      overflow: hidden;
      background: transparent;
    }
    body {
      display: grid;
      place-items: center;
      font-family: "Arial Black", Impact, Arial, sans-serif;
    }
    .slot {
      position: relative;
      width: 285px;
      height: 78px;
      overflow: hidden;
      color: #f8f8f8;
      background: rgba(35, 37, 45, .94);
      border: 3px solid #646978;
      border-radius: 6px;
      text-shadow: 2px 2px 0 #050505, -1px -1px 0 #050505, 1px -1px 0 #050505, -1px 1px 0 #050505;
    }
    .slot.empty {
      opacity: .72;
      filter: grayscale(1);
    }
    .sprite-box {
      position: absolute;
      left: 10px;
      top: 9px;
      width: 58px;
      height: 58px;
      overflow: hidden;
      image-rendering: pixelated;
    }
    .sprite-box img {
      height: 58px;
      width: auto;
      max-width: none;
      image-rendering: pixelated;
    }
    .name {
      position: absolute;
      left: 75px;
      top: 7px;
      width: 142px;
      height: 23px;
      overflow: hidden;
      white-space: nowrap;
      font-size: 16px;
      line-height: 20px;
    }
    .level {
      position: absolute;
      right: 12px;
      top: 8px;
      color: #ffef55;
      font-size: 16px;
      line-height: 20px;
    }
    .hpbar {
      position: absolute;
      left: 75px;
      top: 37px;
      width: 185px;
      height: 13px;
      padding: 2px;
      background: #11151c;
      border: 2px solid #e5e5e5;
      border-radius: 3px;
    }
    .hpfill {
      height: 100%;
      width: 0%;
      background: #30ec49;
      border-radius: 1px;
    }
    .hpfill.mid { background: #f1cf35; }
    .hpfill.low { background: #e63a31; }
    .ps {
      position: absolute;
      left: 75px;
      top: 52px;
      font-size: 16px;
      line-height: 18px;
    }
    .status {
      position: absolute;
      right: 12px;
      bottom: 7px;
      font-size: 13px;
      color: #d8deea;
      text-align: right;
    }
  </style>
</head>
<body>
  <main class="slot empty" id="slot">
    <div class="sprite-box"></div>
    <div class="name">Slot</div>
    <div class="level">Nv.0</div>
    <div class="hpbar"><div class="hpfill"></div></div>
    <div class="ps">PS 0%</div>
    <div class="status">VACIO</div>
  </main>
  <script>
    const slotEl = document.getElementById('slot');
    const slotMatch = location.pathname.match(/\\/team-slot\\/(\\d+)/);
    const wantedSlot = Math.max(1, Math.min(6, Number(slotMatch ? slotMatch[1] : 1)));

    function clean(value) {
      return String(value || '').replace(/[<>&]/g, '');
    }
    function hpPct(mon) {
      const hp = Number(mon.hp || 0);
      const total = Math.max(1, Number(mon.totalhp || 0));
      return Math.max(0, Math.min(100, Math.round((hp / total) * 100)));
    }
    function renderEmpty(text = 'VACIO') {
      slotEl.className = 'slot empty';
      slotEl.innerHTML = `
        <div class="sprite-box"></div>
        <div class="name">Slot ${wantedSlot}</div>
        <div class="level">Nv.0</div>
        <div class="hpbar"><div class="hpfill"></div></div>
        <div class="ps">PS 0%</div>
        <div class="status">${clean(text)}</div>`;
    }
    function renderMon(mon) {
      const pct = hpPct(mon);
      const hpClass = pct <= 25 ? 'low' : pct <= 50 ? 'mid' : '';
      const fainted = !!mon.fainted || Number(mon.hp || 0) <= 0;
      const name = clean(mon.name || mon.species || `Slot ${wantedSlot}`);
      const level = clean(mon.level || 0);
      const sprite = clean(mon.sprite || `/team-sprite/${wantedSlot}.png`);
      slotEl.className = `slot ${fainted ? 'empty' : ''}`;
      slotEl.innerHTML = `
        <div class="sprite-box"><img src="${sprite}?t=${Date.now()}" alt=""></div>
        <div class="name">${name}</div>
        <div class="level">Nv.${level}</div>
        <div class="hpbar"><div class="hpfill ${hpClass}" style="width:${pct}%"></div></div>
        <div class="ps">PS ${pct}%</div>
        <div class="status">${fainted ? 'DEBIL' : 'OK'}</div>`;
    }
    async function refresh() {
      try {
        const response = await fetch('/team.json?t=' + Date.now(), { cache: 'no-store' });
        const payload = await response.json();
        if (!payload.ok) throw new Error(payload.error || 'bad_team_payload');
        const team = payload.team || [];
        const mon = team.find((entry) => Number(entry.slot || 0) === wantedSlot);
        if (!mon) renderEmpty();
        else renderMon(mon);
      } catch (error) {
        renderEmpty('OFFLINE');
      }
    }
    renderEmpty();
    refresh();
    setInterval(refresh, 1000);
  </script>
</body>
</html>
"""

VK = {
    "backspace": 0x08,
    "tab": 0x09,
    "enter": 0x0D,
    "shift": 0x10,
    "ctrl": 0x11,
    "alt": 0x12,
    "esc": 0x1B,
    "space": 0x20,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
}

for i in range(10):
    VK[str(i)] = 0x30 + i
for i, ch in enumerate("abcdefghijklmnopqrstuvwxyz"):
    VK[ch] = 0x41 + i


QT_KEY_MAP = {
    16777234: "left",
    16777235: "up",
    16777236: "right",
    16777237: "down",
    16777219: "backspace",
    16777220: "enter",
    16777216: "esc",
    32: "space",
}

for code in range(48, 58):
    QT_KEY_MAP[code] = chr(code)
for code in range(65, 91):
    QT_KEY_MAP[code] = chr(code).lower()

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
MAPVK_VK_TO_VSC = 0

EXTENDED_KEYS = {
    "left",
    "up",
    "right",
    "down",
    "insert",
    "delete",
    "home",
    "end",
    "pageup",
    "pagedown",
}


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("union", INPUT_UNION)]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_mgba_keys():
    config_path = MGBA_CONFIG_PATH if MGBA_CONFIG_PATH.exists() else PORTABLE_MGBA_CONFIG_PATH
    if not config_path.exists():
        return {}

    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")
    if not parser.has_section("gba.input.QT_K"):
        return {}

    mapping = {
        "keyA": "a",
        "keyB": "b",
        "keyStart": "start",
        "keySelect": "select",
        "keyUp": "up",
        "keyDown": "down",
        "keyLeft": "left",
        "keyRight": "right",
        "keyL": "l",
        "keyR": "r",
    }
    keys = {}
    section = parser["gba.input.QT_K"]
    for mgba_key, logical_key in mapping.items():
        raw = section.get(mgba_key)
        if raw is None:
            continue
        try:
            code = int(raw)
        except ValueError:
            continue
        key_name = QT_KEY_MAP.get(code)
        if key_name:
            keys[logical_key] = key_name
    return keys


def load_config():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    if config.get("server", {}).get("sync_keys_from_mgba", True):
        detected = load_mgba_keys()
        if detected:
            config.setdefault("keys", {}).update(detected)
            config["detected_mgba_keys"] = detected
    return config


def load_manifest():
    if not MANIFEST_PATH.exists():
        return {
            "id": "pokemon-anil-live",
            "gameId": "pokemon-anil-live",
            "name": "Pokemon Anil Live",
            "endpoint": "POST http://127.0.0.1:8765/event",
            "actions": [],
        }
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))


def normalize(value):
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return "".join(ch if ch.isalnum() else " " for ch in text).strip()


def compact_text(value):
    return "".join(normalize(value).split())


def levenshtein(left, right):
    left = compact_text(left)
    right = compact_text(right)
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous = list(range(len(right) + 1))
    for i, lch in enumerate(left, start=1):
        current = [i]
        for j, rch in enumerate(right, start=1):
            cost = 0 if lch == rch else 1
            current.append(min(
                current[j - 1] + 1,
                previous[j] + 1,
                previous[j - 1] + cost,
            ))
        previous = current
    return previous[-1]


def log_event(payload):
    log_path = get_save_root() / "logs" / "events.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=True) + "\n")


def get_save_root():
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not available")
    return Path(appdata) / "Pokemon Anil Live"


def get_save_paths():
    save_root = get_save_root()
    save_root.mkdir(parents=True, exist_ok=True)
    return sorted(save_root.glob("Partida *.rxdata"))


def get_game_save_root(config=None):
    config = config or load_config()
    command_file = ROOT / config["file_bridge"]["command_file"]
    return command_file.parent


def backup_save_file(save_path, reason, backup_dir=None):
    if not save_path.exists():
        return None
    save_root = get_save_root()
    backup_root = Path(backup_dir) if backup_dir else save_root / "backups" / "autosaves"
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_reason = normalize(reason).replace(" ", "_") or "backup"
    backup_path = backup_root / f"{save_path.stem}_{safe_reason}_{stamp}{save_path.suffix}"
    shutil.copy2(save_path, backup_path)
    return backup_path


def cleanup_old_backups(backup_dir, keep=60):
    backup_dir = Path(backup_dir)
    if keep <= 0 or not backup_dir.exists():
        return
    backups = sorted(
        (path for path in backup_dir.glob("*.rxdata") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for old_path in backups[keep:]:
        try:
            old_path.unlink()
        except OSError:
            pass


def snapshot_save_state():
    state = {}
    for save_path in get_save_paths():
        try:
            stat = save_path.stat()
        except OSError:
            continue
        state[str(save_path)] = (stat.st_mtime_ns, stat.st_size)
    return state


def backup_existing_saves(reason):
    backups = []
    for save_path in get_save_paths():
        backup_path = backup_save_file(save_path, reason)
        if backup_path:
            backups.append(str(backup_path))
    cleanup_old_backups(get_save_root() / "backups" / "autosaves")
    if backups:
        log_event({"time": now_iso(), "save_backup": {"reason": reason, "backups": backups}})
    return backups


def sync_game_saves_to_appdata(reason):
    try:
        game_save_root = get_game_save_root()
    except Exception as exc:
        log_event({"time": now_iso(), "save_sync_error": str(exc)})
        return []
    if not game_save_root.exists():
        return []

    save_root = get_save_root()
    backup_root = save_root / "backups" / "autosaves"
    synced = []
    for game_save in sorted(game_save_root.glob("Partida *.rxdata")):
        app_save = save_root / game_save.name
        try:
            game_stat = game_save.stat()
            should_copy = not app_save.exists()
            if not should_copy:
                app_stat = app_save.stat()
                should_copy = game_stat.st_mtime_ns > app_stat.st_mtime_ns
            if should_copy:
                if app_save.exists():
                    backup_save_file(app_save, "before_game_sync", backup_dir=backup_root)
                shutil.copy2(game_save, app_save)
                backup_save_file(app_save, reason, backup_dir=backup_root)
                synced.append(str(app_save))
        except OSError as exc:
            log_event({"time": now_iso(), "save_sync_error": {"path": str(game_save), "error": str(exc)}})

    if synced:
        cleanup_old_backups(backup_root)
        log_event({"time": now_iso(), "save_sync": {"reason": reason, "synced": synced}})
    return synced


def save_monitor_loop(interval_seconds=2):
    global SAVE_MONITOR_STATE
    sync_game_saves_to_appdata("startup_game_folder")
    SAVE_MONITOR_STATE = snapshot_save_state()
    backup_existing_saves("startup")
    while True:
        time.sleep(interval_seconds)
        try:
            sync_game_saves_to_appdata("game_save")
            current_state = snapshot_save_state()
            changed = [
                Path(path)
                for path, file_state in current_state.items()
                if SAVE_MONITOR_STATE.get(path) != file_state
            ]
            for save_path in changed:
                backup_save_file(save_path, "autosave")
            if changed:
                cleanup_old_backups(get_save_root() / "backups" / "autosaves")
                log_event({
                    "time": now_iso(),
                    "save_backup": {
                        "reason": "autosave",
                        "changed": [str(path) for path in changed],
                    },
                })
            SAVE_MONITOR_STATE = current_state
        except Exception as exc:
            log_event({"time": now_iso(), "save_monitor_error": str(exc)})
            time.sleep(5)


def ensure_save_monitor_started():
    global SAVE_MONITOR_STARTED
    if SAVE_MONITOR_STARTED:
        return
    monitor = threading.Thread(target=save_monitor_loop, daemon=True)
    monitor.start()
    SAVE_MONITOR_STARTED = True


def send_lua_command(config, command, event_id=None, timeout_ms=1200):
    bridge = config.get("lua_bridge", {})
    host = bridge.get("host", "127.0.0.1")
    port = int(bridge.get("port", 8788))
    message = f"{command} {event_id or f'manual-{int(time.time() * 1000)}'}\n"
    timeout = max(0.1, int(timeout_ms) / 1000)
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(message.encode("utf-8"))
            response = sock.recv(2048).decode("utf-8", errors="replace").strip()
    except OSError as exc:
        raise RuntimeError(
            f"Lua bridge not connected at {host}:{port}. "
            "Load tools/mgba_live_bridge.lua in mGBA first."
        ) from exc
    payload = {"time": now_iso(), "command": command, "event_id": event_id, "response": response}
    result_path = get_save_root() / "logs" / "lua_socket_events.jsonl"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with result_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=True) + "\n")
    if not response.startswith("OK"):
        raise RuntimeError(f"Lua bridge rejected command: {response}")
    return {"ok": True, "lua_command": command, "lua_response": response}


def send_lua_item_quantity(config, command, quantity, event_id=None, timeout_ms=1200):
    quantity = max(1, min(99, int(quantity)))
    marker = event_id or f"manual-{int(time.time() * 1000)}"
    return send_lua_command(config, command, event_id=f"{quantity} {marker}", timeout_ms=timeout_ms)


def send_file_command(config, command, event_id=None, timeout_ms=1200):
    bridge = config.get("file_bridge", {})
    command_file = bridge.get("command_file")
    if not command_file:
        raise RuntimeError("file_bridge.command_file is not configured.")
    path = Path(command_file)
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    marker = event_id or f"manual-{int(time.time() * 1000)}"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"{command} {marker}\n")
    return {"ok": True, "file_command": command, "command_file": str(path)}


def send_file_item_quantity(config, command, quantity, event_id=None, timeout_ms=1200):
    quantity = max(1, min(99, int(quantity)))
    marker = event_id or f"manual-{int(time.time() * 1000)}"
    return send_file_command(config, command, event_id=f"{quantity} {marker}", timeout_ms=timeout_ms)


def send_file_button(config, button, frames=12, timeout_ms=1200):
    return send_file_command(config, "press", event_id=f"{button} {frames}", timeout_ms=timeout_ms)


def send_file_combo(config, buttons, press_frames=6, gap_frames=4, timeout_ms=1200):
    results = []
    for button in buttons:
        results.append(send_file_button(config, button, frames=press_frames, timeout_ms=timeout_ms))
    return {"ok": True, "file_command": "combo", "count": len(results), "button_results": results[-5:]}


def send_lua_button(config, button, frames=6, timeout_ms=1200):
    return send_lua_command(config, "press", event_id=f"{button} {frames}", timeout_ms=timeout_ms)


def send_lua_combo(config, buttons, press_frames=6, gap_frames=4, timeout_ms=1200):
    cleaned = [normalize(button) for button in buttons if normalize(button)]
    if not cleaned:
        return {"ok": True, "lua_command": "combo", "skipped": True, "reason": "empty_combo"}
    sequence = ",".join(cleaned)
    return send_lua_command(
        config,
        "combo",
        event_id=f"{sequence} {press_frames} {gap_frames}",
        timeout_ms=timeout_ms,
    )


def find_window_handle(title_contains):
    if not title_contains:
        return None

    needle = normalize(title_contains)
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_proc(hwnd, _lparam):
        if not ctypes.windll.user32.IsWindowVisible(hwnd):
            return True
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value
        if needle in normalize(title):
            found.append(hwnd)
            return False
        return True

    ctypes.windll.user32.EnumWindows(enum_proc, 0)
    return found[0] if found else None


def focus_target(config):
    if not config["server"].get("focus_before_action", True):
        return True
    hwnd = find_window_handle(config["server"].get("target_window_contains", "mGBA"))
    if not hwnd:
        return False
    ctypes.windll.user32.ShowWindow(hwnd, 5)
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    time.sleep(0.08)
    return True


def send_key(key_name, hold_ms=55):
    key = normalize(key_name)
    if key not in VK:
        raise ValueError(f"Unknown key: {key_name}")
    vk = VK[key]
    scan = ctypes.windll.user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    flags = KEYEVENTF_SCANCODE
    if key in EXTENDED_KEYS:
        flags |= KEYEVENTF_EXTENDEDKEY
    extra = ctypes.c_ulong(0)
    down = INPUT(type=INPUT_KEYBOARD, union=INPUT_UNION(ki=KEYBDINPUT(0, scan, flags, 0, ctypes.pointer(extra))))
    up = INPUT(type=INPUT_KEYBOARD, union=INPUT_UNION(ki=KEYBDINPUT(0, scan, flags | KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))))
    ctypes.windll.user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT))
    time.sleep(max(0, hold_ms) / 1000)
    ctypes.windll.user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT))


def resolve_key(config, logical_key):
    return config.get("keys", {}).get(logical_key, logical_key)


def logical_key_from_raw(config, raw_key):
    key = normalize(raw_key)
    reverse = {normalize(value): logical for logical, value in config.get("keys", {}).items()}
    return reverse.get(key, key)


def restart_save(config):
    save_dir = get_save_root()
    save_paths = get_save_paths()
    command_file = ROOT / config["file_bridge"]["command_file"]
    game_dir = command_file.parent
    game_exe = game_dir / "Game.exe"
    backup_dir = save_dir / "backups" / "manual"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backups = []

    for index, save_path in enumerate(save_paths, start=1):
        backup_path = backup_dir / f"save_before_restart_{stamp}_{index}.rxdata"
        shutil.copy2(save_path, backup_path)
        backups.append(str(backup_path))

    return {
        "ok": True,
        "deleted_saves": 0,
        "deleted_paths": [],
        "backups": backups,
        "game_restarted": False,
        "note": "Safe mode: saves were backed up only. The game was not closed or restarted.",
    }


def run_action(config, action_name, dry_run=False):
    actions = config.get("actions", {})
    action = actions.get(action_name)
    if not action:
        raise ValueError(f"Action not found in config: {action_name}")

    if dry_run:
        return {"ok": True, "dry_run": True, "action": action_name}

    use_file_input = bool(config.get("file_bridge", {}).get("use_for_input", False))
    use_lua_input = bool(config.get("lua_bridge", {}).get("use_for_input", True)) and not use_file_input
    needs_window_input = action["type"] in ("sequence", "random_keys") and not use_lua_input and not use_file_input
    if needs_window_input and not focus_target(config):
        raise RuntimeError("Could not find target emulator window. Open mGBA first.")

    button_results = []
    if action["type"] == "sequence":
        if use_file_input:
            buttons = []
            for step in action.get("steps", []):
                presses = int(step.get("presses", 1))
                buttons.extend([step["key"]] * presses)
            button_result = send_file_combo(config, buttons)
            button_results.append(button_result)
            return {"ok": True, "action": action_name, "input_mode": "file_combo", "button_results": button_results[-5:]}
        if use_lua_input:
            buttons = []
            for step in action.get("steps", []):
                presses = int(step.get("presses", 1))
                buttons.extend([step["key"]] * presses)
            button_result = send_lua_combo(config, buttons)
            button_results.append(button_result)
            if not button_result.get("ok"):
                return {"ok": False, "action": action_name, "button_results": button_results}
            result = {"ok": True, "action": action_name, "input_mode": "lua_combo", "button_results": button_results[-5:]}
            return result
        for step in action.get("steps", []):
            logical_key = step["key"]
            key = resolve_key(config, logical_key)
            presses = int(step.get("presses", 1))
            delay_ms = int(step.get("delay_ms", 100))
            for _ in range(presses):
                if use_lua_input:
                    button_result = send_lua_button(config, logical_key)
                    button_results.append(button_result)
                    if not button_result.get("ok"):
                        return {"ok": False, "action": action_name, "button_results": button_results}
                else:
                    send_key(key)
                time.sleep(delay_ms / 1000)
    elif action["type"] == "random_keys":
        keys = action.get("keys", [])
        presses = int(action.get("presses", 1))
        delay_ms = int(action.get("delay_ms", 100))
        if use_file_input:
            buttons = [random.choice(keys) for _ in range(presses)]
            press_frames = max(12, min(18, round(delay_ms / 16)))
            button_result = send_file_combo(config, buttons, press_frames=press_frames)
            button_results.append(button_result)
            return {"ok": True, "action": action_name, "input_mode": "file_combo", "button_results": button_results[-5:]}
        if use_lua_input:
            buttons = [random.choice(keys) for _ in range(presses)]
            press_frames = max(2, min(18, round(delay_ms / 16)))
            button_result = send_lua_combo(config, buttons, press_frames=press_frames, gap_frames=3)
            button_results.append(button_result)
            if not button_result.get("ok"):
                return {"ok": False, "action": action_name, "button_results": button_results}
            return {"ok": True, "action": action_name, "input_mode": "lua_combo", "button_results": button_results[-5:]}
        for _ in range(presses):
            logical_key = random.choice(keys)
            key = resolve_key(config, logical_key)
            if use_lua_input:
                button_result = send_lua_button(config, logical_key)
                button_results.append(button_result)
                if not button_result.get("ok"):
                    return {"ok": False, "action": action_name, "button_results": button_results}
            else:
                send_key(key)
            time.sleep(delay_ms / 1000)
    elif action["type"] == "lua_command":
        return send_lua_command(
            config,
            action["command"],
            event_id=action.get("event_id"),
            timeout_ms=int(action.get("timeout_ms", 1200)),
        )
    elif action["type"] == "file_command":
        return send_file_command(
            config,
            action["command"],
            event_id=action.get("event_id"),
            timeout_ms=int(action.get("timeout_ms", 1200)),
        )
    elif action["type"] == "file_sequence":
        commands = action.get("commands", [])
        delay_ms = int(action.get("delay_ms", 0))
        results = []
        for index, command in enumerate(commands):
            results.append(send_file_command(config, command))
            if delay_ms > 0 and index < len(commands) - 1:
                time.sleep(delay_ms / 1000)
        return {
            "ok": True,
            "action": action_name,
            "input_mode": "file_sequence",
            "count": len(results),
            "delay_ms": delay_ms,
        }
    elif action["type"] == "restart_save":
        return restart_save(config)
    else:
        raise ValueError(f"Unknown action type: {action['type']}")

    result = {"ok": True, "action": action_name}
    if button_results:
        result["input_mode"] = "lua"
        result["button_results"] = button_results[-5:]
    return result


def run_raw_key(config, key_name, dry_run=False):
    key = normalize(key_name)
    if dry_run:
        return {"ok": True, "dry_run": True, "raw_key": key}
    if config.get("file_bridge", {}).get("use_for_input", False):
        result = send_file_button(config, key)
        result["raw_key"] = key
        result["input_mode"] = "file_button"
        return result
    if config.get("lua_bridge", {}).get("use_for_input", True):
        logical_key = logical_key_from_raw(config, key)
        result = send_lua_button(config, logical_key)
        result["raw_key"] = key
        result["lua_button"] = logical_key
        return result
    if not focus_target(config):
        raise RuntimeError("Could not find target emulator window. Open mGBA first.")
    send_key(key)
    return {"ok": True, "raw_key": key}


def execute_event_payload(config, payload):
    event_id = payload.get("event_id") or payload.get("eventId")
    raw_key = payload.get("raw_key") or payload.get("rawKey")
    source = payload.get("source") or {}
    action = payload.get("action") or action_from_gift(
        config,
        gift_id=payload.get("gift_id") or payload.get("giftId") or source.get("gift_id") or source.get("giftId"),
        gift_name=payload.get("gift_name") or payload.get("giftName") or source.get("gift_name") or source.get("giftName"),
    )
    if raw_key:
        if not config.get("server", {}).get("allow_raw_keys", True):
            raise ValueError("raw_key is disabled for this game runtime. Send a manifest action instead.")
        result = run_raw_key(config, raw_key, dry_run=bool(payload.get("dry_run")))
        result["event_id"] = event_id
        result["resolved_action"] = f"raw_key:{raw_key}"
        return result
    if not action:
        raise ValueError("No action matched. Send action or configured gift_name.")
    if action in config.get("actions", {}) and config["actions"][action].get("type") in ("lua_command", "file_command"):
        config["actions"][action]["event_id"] = event_id
        action_config = config["actions"][action]
        quantity = int(payload.get("quantity", 1))
        if quantity > 1 and action_config.get("aggregate_quantity", False):
            sender = send_file_item_quantity if action_config.get("type") == "file_command" else send_lua_item_quantity
            result = sender(config, action_config["command"], quantity, event_id=event_id, timeout_ms=int(action_config.get("timeout_ms", 1200)))
            result["event_id"] = event_id
            result["resolved_action"] = action
            result["quantity"] = min(quantity, 99)
            return result
    result = run_action(config, action, dry_run=bool(payload.get("dry_run")))
    result["event_id"] = event_id
    result["resolved_action"] = action
    return result


def remember_queue_result(record):
    with QUEUE_LOCK:
        RECENT_QUEUE_RESULTS.append(record)
        del RECENT_QUEUE_RESULTS[:-25]


def queue_worker():
    while True:
        payload = ACTION_QUEUE.get()
        event_id = payload.get("event_id") or payload.get("eventId")
        started = now_iso()
        try:
            config = load_config()
            result = execute_event_payload(config, payload)
            result["queued_execution"] = True
            log_event({"time": now_iso(), "queued_request": payload, "started": started, "result": result})
            remember_queue_result({"time": now_iso(), "event_id": event_id, "ok": True, "result": result})
        except Exception as exc:
            error = {"ok": False, "event_id": event_id, "queued_execution": True, "error": str(exc)}
            log_event({"time": now_iso(), "queued_request": payload, "started": started, "result": error})
            remember_queue_result({"time": now_iso(), "event_id": event_id, "ok": False, "result": error})
        finally:
            with QUEUE_LOCK:
                if event_id:
                    QUEUED_EVENT_IDS.discard(event_id)
                    PROCESSED_EVENT_IDS.add(event_id)
            ACTION_QUEUE.task_done()
            config = load_config()
            cooldown_ms = int(config.get("queue", {}).get("cooldown_ms", 180))
            time.sleep(max(0, cooldown_ms) / 1000)


def ensure_worker_started():
    global WORKER_STARTED
    if WORKER_STARTED:
        return
    worker = threading.Thread(target=queue_worker, daemon=True)
    worker.start()
    WORKER_STARTED = True


def enqueue_event(config, payload):
    event_id = payload.get("event_id") or payload.get("eventId")
    queue_config = config.get("queue", {})
    max_size = int(queue_config.get("max_size", 80))
    with QUEUE_LOCK:
        if event_id and (event_id in QUEUED_EVENT_IDS or event_id in PROCESSED_EVENT_IDS):
            return {"ok": True, "duplicate": True, "queued": False, "event_id": event_id}
        if max_size > 0 and ACTION_QUEUE.qsize() >= max_size:
            return {
                "ok": False,
                "queued": False,
                "error": "queue_full",
                "queue_size": ACTION_QUEUE.qsize(),
                "max_size": max_size,
            }
        if event_id:
            QUEUED_EVENT_IDS.add(event_id)
        ACTION_QUEUE.put(payload)
        return {
            "ok": True,
            "queued": True,
            "event_id": event_id,
            "queue_size": ACTION_QUEUE.qsize(),
            "max_size": max_size,
        }


def action_from_gift(config, gift_id=None, gift_name=None):
    normalized_name = normalize(gift_name)
    compact_name = compact_text(gift_name)
    fuzzy_candidates = []
    for rule in config.get("gift_rules", []):
        if not rule.get("enabled", True):
            continue
        if gift_id is not None and rule.get("gift_id") == gift_id:
            return rule["action"]
        aliases = [normalize(alias) for alias in rule.get("aliases", [])]
        if normalized_name and normalized_name in aliases:
            return rule["action"]
        if compact_name:
            for alias in aliases:
                distance = levenshtein(compact_name, alias)
                fuzzy_candidates.append((distance, len(compact_text(alias)), rule["action"], alias))

    matching = config.get("matching", {})
    if matching.get("allow_fuzzy_gift_names", False) and fuzzy_candidates:
        fuzzy_candidates.sort(key=lambda item: item[0])
        distance, alias_length, action, _alias = fuzzy_candidates[0]
        limit = int(
            matching.get(
                "max_fuzzy_distance_short" if alias_length <= 5 else "max_fuzzy_distance_long",
                1 if alias_length <= 5 else 2,
            )
        )
        if distance <= limit:
            return action
    return None


def live_chaos_log_path(config):
    command_file = config.get("file_bridge", {}).get("command_file")
    if command_file:
        return Path(command_file).with_name("live_chaos_log.txt")
    return ROOT / "logs" / "live_chaos_log.txt"


def latest_lottery_status(config):
    log_path = live_chaos_log_path(config)
    lines = []
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-120:]
    for index, line in enumerate(reversed(lines)):
        if "pokemon_lottery_status " not in line:
            continue
        detail = line.split("pokemon_lottery_status ", 1)[-1].strip()
        if " skipped:" in line:
            return {
                "ok": True,
                "active": True,
                "id": f"{len(lines) - index}:{line}",
                "line": line,
                "code": "SKIP",
                "amount": "0/0",
                "summary": "",
            }
        if " failed:" in line:
            return {
                "ok": True,
                "active": False,
                "id": f"{len(lines) - index}:{line}",
                "line": line,
                "summary": detail,
            }
        parts = detail.split(None, 2)
        return {
            "ok": True,
            "active": True,
            "id": f"{len(lines) - index}:{line}",
            "line": line,
            "code": parts[0] if parts else "",
            "amount": parts[1] if len(parts) > 1 else "",
            "summary": parts[2] if len(parts) > 2 else detail,
        }
    return {"ok": True, "active": False, "id": "", "summary": "", "line": ""}


def pokemon_front_sprite_path(member):
    species = str(member.get("species") or "UNKNOWN").upper()
    form = int(member.get("form") or 0)
    shiny = bool(member.get("shiny"))
    base_dir = ROOT / "POKEMON_ANIL" / "Pokemon Anil" / "Graphics" / "Pokemon"
    primary = base_dir / ("Front shiny" if shiny else "Front")
    fallback = base_dir / "Front"
    candidates = []
    if form > 0:
        candidates.append(primary / f"{species}_{form}.png")
    candidates.append(primary / f"{species}.png")
    if form > 0:
        candidates.append(fallback / f"{species}_{form}.png")
    candidates.append(fallback / f"{species}.png")
    candidates.append(fallback / "000.png")
    return next((path for path in candidates if path.exists()), None)


class ChaosHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Requested-With")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Max-Age", "86400")

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_cors_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, status, body, content_type, cache=False):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self._send_cors_headers()
        if not cache:
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/panel"):
            body = PANEL_HTML.encode("utf-8")
            self._send_bytes(200, body, "text/html; charset=utf-8")
            return
        if parsed.path == "/team-overlay":
            body = TEAM_OVERLAY_HTML.encode("utf-8")
            self._send_bytes(200, body, "text/html; charset=utf-8")
            return
        if parsed.path.startswith("/team-slot/"):
            raw_slot = parsed.path.rsplit("/", 1)[-1]
            if raw_slot.isdigit() and 1 <= int(raw_slot) <= 6:
                body = TEAM_SLOT_OVERLAY_HTML.encode("utf-8")
                self._send_bytes(200, body, "text/html; charset=utf-8")
            else:
                self._send_json(404, {"ok": False, "error": "slot_not_found"})
            return
        if parsed.path == "/team.json":
            if TEAM_JSON_PATH.exists():
                body = TEAM_JSON_PATH.read_bytes()
                self._send_bytes(200, body, "application/json; charset=utf-8")
            else:
                self._send_json(200, {
                    "ok": False,
                    "error": "team_not_ready",
                    "team": [],
                    "path": str(TEAM_JSON_PATH),
                })
            return
        if parsed.path.startswith("/team-sprite/") and parsed.path.endswith(".png"):
            name = Path(parsed.path).name
            if name.startswith("slot") and name[4:-4].isdigit():
                sprite_path = TEAM_SPRITE_DIR / name
            elif name[:-4].isdigit():
                sprite_path = TEAM_SPRITE_DIR / f"slot{name[:-4]}.png"
            else:
                sprite_path = None
            if sprite_path and sprite_path.exists():
                self._send_bytes(200, sprite_path.read_bytes(), "image/png", cache=False)
            else:
                self._send_json(404, {"ok": False, "error": "sprite_not_found"})
            return
        if parsed.path.startswith("/team-front/") and parsed.path.endswith(".png"):
            raw_slot = Path(parsed.path).name[:-4]
            if raw_slot.startswith("slot"):
                raw_slot = raw_slot[4:]
            if not raw_slot.isdigit() or not TEAM_JSON_PATH.exists():
                self._send_json(404, {"ok": False, "error": "front_sprite_not_found"})
                return
            payload = json.loads(TEAM_JSON_PATH.read_text(encoding="utf-8", errors="replace"))
            member = next((item for item in payload.get("team", []) if int(item.get("slot") or 0) == int(raw_slot)), None)
            sprite_path = pokemon_front_sprite_path(member or {})
            if sprite_path and sprite_path.exists():
                self._send_bytes(200, sprite_path.read_bytes(), "image/png", cache=False)
            else:
                self._send_json(404, {"ok": False, "error": "front_sprite_not_found"})
            return
        if parsed.path.startswith("/party-ui/") and parsed.path.endswith(".png"):
            name = Path(parsed.path).name
            party_assets = {
                "ptpanel_rect_desel.png",
                "ptpanel_rect_faint.png",
                "ptpanel_blank.png",
                "overlay_hp_back.png",
                "overlay_hp.png",
                "shiny.png",
                "shiny_ur.png",
            }
            root_assets = {
                "statuses.png",
            }
            if name in party_assets:
                asset_path = PARTY_UI_DIR / name
            elif name in root_assets:
                asset_path = GAME_UI_ROOT / name
            else:
                asset_path = None
            if asset_path and asset_path.exists():
                self._send_bytes(200, asset_path.read_bytes(), "image/png", cache=True)
            else:
                self._send_json(404, {"ok": False, "error": "party_ui_asset_not_found"})
            return
        if parsed.path == "/health":
            self._send_json(200, {"ok": True, "service": "pokemon_anil_live"})
            return
        if parsed.path in ("/manifest", "/game-manifest.json"):
            self._send_json(200, load_manifest())
            return
        if parsed.path in ("/actions", "/api/actions"):
            manifest = load_manifest()
            self._send_json(200, {
                "ok": True,
                "gameId": manifest.get("gameId") or manifest.get("id"),
                "endpoint": manifest.get("endpoint"),
                "actions": manifest.get("actions", []),
            })
            return
        if parsed.path == "/api/keys":
            config = load_config()
            self._send_json(200, {
                "ok": True,
                "keys": config.get("keys", {}),
                "detected_mgba_keys": config.get("detected_mgba_keys", {}),
                "source": str(MGBA_CONFIG_PATH if MGBA_CONFIG_PATH.exists() else PORTABLE_MGBA_CONFIG_PATH),
            })
            return
        if parsed.path == "/api/queue":
            with QUEUE_LOCK:
                payload = {
                    "ok": True,
                    "queue_size": ACTION_QUEUE.qsize(),
                    "queued_event_ids": len(QUEUED_EVENT_IDS),
                    "processed_event_ids": len(PROCESSED_EVENT_IDS),
                    "recent": RECENT_QUEUE_RESULTS[-10:],
                }
            self._send_json(200, payload)
            return
        if parsed.path == "/api/live-log":
            config = load_config()
            log_path = live_chaos_log_path(config)
            lines = []
            if log_path.exists():
                lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
            self._send_json(200, {"ok": True, "path": str(log_path), "lines": lines})
            return
        if parsed.path == "/api/lottery-status":
            self._send_json(200, latest_lottery_status(load_config()))
            return
        self._send_json(404, {"ok": False, "error": "not_found"})

    def do_POST(self):
        if self.path not in ("/event", "/batch"):
            self._send_json(404, {"ok": False, "error": "not_found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
            config = load_config()
            if self.path == "/batch":
                action = payload.get("action")
                count = int(payload.get("count", 1))
                if not action:
                    raise ValueError("Batch needs action.")
                if count < 1:
                    count = 1
                if count > 250:
                    count = 250
                batch_id = payload.get("batch_id") or f"batch-{int(time.time() * 1000)}"
                action_config = config.get("actions", {}).get(action, {})
                if action_config.get("type") == "lua_command" and action_config.get("aggregate_quantity", False):
                    item = {
                        "event_id": f"{batch_id}-{action}-qty",
                        "action": action,
                        "quantity": count,
                    }
                    result = enqueue_event(config, item)
                    response = {
                        "ok": result.get("ok", False),
                        "batch_id": batch_id,
                        "action": action,
                        "requested": count,
                        "enqueued": 1 if result.get("queued") else 0,
                        "aggregated": True,
                        "quantity": min(count, 99),
                        "queue_size": ACTION_QUEUE.qsize(),
                        "last_result": result,
                    }
                    log_event({"time": now_iso(), "batch_request": payload, "result": response})
                    self._send_json(200 if response["ok"] else 429, response)
                    return

                results = []
                enqueued = 0
                rejected = 0
                for index in range(count):
                    item = {
                        "event_id": f"{batch_id}-{action}-{index + 1}",
                        "action": action,
                    }
                    result = enqueue_event(config, item)
                    results.append(result)
                    if result.get("ok") and result.get("queued"):
                        enqueued += 1
                    elif not result.get("ok"):
                        rejected += 1
                        break
                response = {
                    "ok": rejected == 0,
                    "batch_id": batch_id,
                    "action": action,
                    "requested": count,
                    "enqueued": enqueued,
                    "rejected": rejected,
                    "queue_size": ACTION_QUEUE.qsize(),
                    "last_result": results[-1] if results else None,
                }
                log_event({"time": now_iso(), "batch_request": payload, "result": response})
                self._send_json(200 if response["ok"] else 429, response)
                return

            event_id = payload.get("event_id") or payload.get("eventId")
            queue_enabled = bool(config.get("queue", {}).get("enabled", True))
            if queue_enabled and not payload.get("dry_run"):
                result = enqueue_event(config, payload)
            else:
                with QUEUE_LOCK:
                    if event_id and event_id in PROCESSED_EVENT_IDS:
                        result = {"ok": True, "duplicate": True, "event_id": event_id}
                    else:
                        result = None
                if result is None:
                    result = execute_event_payload(config, payload)
                    with QUEUE_LOCK:
                        if event_id:
                            PROCESSED_EVENT_IDS.add(event_id)
            log_event({"time": now_iso(), "request": payload, "result": result})
            self._send_json(200 if result.get("ok") else 429, result)
        except Exception as exc:
            error = {"ok": False, "error": str(exc)}
            log_event({"time": now_iso(), "request_raw": raw.decode("utf-8", errors="replace"), "result": error})
            self._send_json(400, error)

    def log_message(self, _format, *_args):
        return


def serve():
    ensure_worker_started()
    ensure_save_monitor_started()
    config = load_config()
    host = config["server"].get("host", "127.0.0.1")
    port = int(config["server"].get("port", 8765))
    server = ThreadingHTTPServer((host, port), ChaosHandler)
    print(f"Pokemon Anil Live event bus listening on http://{host}:{port}")
    print("POST /event with {\"action\":\"add_potion_live\"}")
    server.serve_forever()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true", help="Start local HTTP event server")
    parser.add_argument("--action", help="Run one configured action")
    parser.add_argument("--gift-name", help="Resolve a gift name through config and run its action")
    parser.add_argument("--dry-run", action="store_true", help="Validate without pressing keys")
    args = parser.parse_args()

    if args.serve:
        serve()
        return

    config = load_config()
    action = args.action
    if args.gift_name:
        action = action_from_gift(config, gift_name=args.gift_name)
        if not action:
            raise SystemExit(f"No action configured for gift: {args.gift_name}")
    if not action:
        raise SystemExit("Use --serve, --action ACTION, or --gift-name NAME")
    result = run_action(config, action, dry_run=args.dry_run)
    log_event({"time": now_iso(), "manual": True, "action": action, "result": result})
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()

