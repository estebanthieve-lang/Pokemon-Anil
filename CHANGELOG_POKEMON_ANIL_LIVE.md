# Changelog Pokemon Anil Live

## Limpieza inicial reversible - 2026-06-12

- Se movieron `logs/`, `__pycache__/` y zips viejos de `updates/` a `C:\Users\usuario\Music\Pokemon_Anil_Live_NO_COMPARTIR_ARCHIVO\limpieza_20260612_inicial`.
- Se dejo `updates/pokemon-anil-update-0.1.21.zip` en la carpeta viva.
- Se corrigio `assets/acciones_png/INDEX_ACCIONES_IMAGENES.json` para usar rutas relativas en vez de rutas `C:\Users\usuario\...`.
- No se tocaron partidas, `POKEMON_ANIL`, `.git`, GitHub ni logica del juego.

## Overlay front sprite - 2026-06-12

- Los overlays de slot usan el sprite grande `/team-front/{slot}.png` como imagen principal.
- Si el sprite grande falla, vuelven al icono anterior `/team-sprite/{slot}.png`.
- El sprite se anima suavemente por CSS y no se recarga cada segundo si el Pokemon no cambio.
- Backup de los archivos editados: `C:\Users\usuario\Music\Pokemon_Anil_Live_NO_COMPARTIR_ARCHIVO\overlay_backup_front_sprite_20260612`.

## Overlay front sprite estable - 2026-06-12

- Se ajusto el overlay para tratar los sprites `Front` como spritesheets horizontales.
- Por defecto muestra un frame completo, centrado y escalado dentro del cuadro para evitar cortes o desapariciones.
- La animacion completa de frames queda experimental con `?anim=frames`; el modo normal usa solo movimiento idle suave.
- Se valido con especies de distintos tamanos: Eternatus, Lugia, Snorunt, Makuhita, Kadabra y Zygarde.
- Backup de esta fase: `C:\Users\usuario\Music\Pokemon_Anil_Live_NO_COMPARTIR_ARCHIVO\overlay_sprite_frames_backup_20260612_200432`.

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
