# Changelog Pokemon Anil Live

## Estado actual - 2026-06-12

- Runtime del juego conectado por event bus local en `http://127.0.0.1:8877`.
- Partidas separadas en `%APPDATA%\Pokemon Anil Live` para no mezclarse con Pokemon Anil normal.
- Acciones live procesadas en cola, maximo 5 por tick, con reintentos si el juego esta en escena insegura.
- Acciones de objetos funcionan en combate y fuera de combate.
- Acciones de equipo/PS/estado funcionan en combate y fuera de combate con sincronizacion del battler activo.
- Encuentro legendario queda en cola si hay combate, cooldown, escena insegura o no hay Pokemon vivos.
- Encuentro legendario espera el blackout/Centro Pokemon antes de lanzarse si el jugador queda sin Pokemon vivos.
- Encuentro legendario ya no usa `canLose`, para que perder contra el legendario haga el flujo normal de derrota.
- `Curar Pokemon` cura solo Pokemon vivos; no revive debilitados.
- `Restaurar todo` revive y cura todo el equipo.
- `Todos a 1 PS` y `Todos a 50% de vida` solo afectan Pokemon vivos; no reviven debilitados.
- `Sorteo Pokemon negativo` no apunta a Pokemon debilitados.
- Overlay de equipo exporta JSON y sprites a `%APPDATA%\Pokemon Anil Live\team_overlay`.

## Archivos importantes

- Juego compilado: `POKEMON_ANIL/Pokemon Anil/Data/Scripts.rxdata`
- Config acciones event bus: `config/actions_anil.json`
- Manifest para la base TikTok: `game-manifest.json`
- Actualizador: `ACTUALIZAR POKEMON ANIL LIVE.cmd` y `runtime/actualizar_juego.ps1`
- Config del actualizador: `game.config.json`

## Regla de update

Antes de subir o empaquetar, confirmar que los cambios pendientes incluyan como minimo:

- `POKEMON_ANIL/Pokemon Anil/Data/Scripts.rxdata`
- `config/actions_anil.json` si cambio alguna accion
- `game-manifest.json` si cambio el manifest visible para la base
- `game.config.json` o `runtime/actualizar_juego.ps1` si cambio el sistema de updates

