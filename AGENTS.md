# Reglas Pokemon Anil Live

- Ser eficiente: revisar logs y codigo antes de tocar algo; no adivinar.
- Si la instruccion es ambigua, riesgosa o implica subir/borrar/empaquetar, hacer una pregunta corta antes de ejecutar.
- Evitar gastar tokens: responder breve, leer solo archivos relevantes y no repetir pruebas si no aportan informacion nueva.
- No subir a GitHub ni crear ZIP si el usuario no lo pide explicitamente.
- Antes de entregar cambios en `Scripts.rxdata`, probar que `Game.exe` arranque al menos 25 segundos y confirmar que `errorlog.txt` no cambie.
- Nunca tocar partidas guardadas del usuario. Las partidas viven en `%APPDATA%\Pokemon Anil Live`; el actualizador solo debe guardar backups ahi, no borrar saves.
- Todo cambio funcional del juego debe quedar en la version final de `POKEMON_ANIL/Pokemon Anil/Data/Scripts.rxdata` y, si aplica, en `config/actions_anil.json` y `game-manifest.json`.
- Si se cambia una accion del manifest, actualizar tambien la config que ejecuta el event bus.
- Para updates de amigos, asegurar que el paquete incluya todos los archivos tocados y que `ACTUALIZAR POKEMON ANIL LIVE.cmd` use el paquete correcto.
- Mantener un changelog local de cambios importantes para que otro chat pueda continuar sin depender del contexto.
