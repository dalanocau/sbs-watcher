# Verificador SBS en Flask

Este proyecto verifica si existe un nuevo archivo mensual publicado por la SBS y actualiza una hoja de Google Sheets. Además, envía una notificación por Telegram si se detecta un nuevo archivo.

## Archivos

- `app.py`: servidor Flask
- `verificador.py`: lógica principal de verificación
- `requirements.txt`: dependencias del proyecto
- `credentials.json`: tu clave de Google (no se sube a GitHub)
- `.gitignore`: ignora archivos sensibles

## Instrucciones

1. Clona el repo en tu máquina o despliega en Render.
2. Asegúrate de subir `credentials.json` como archivo privado en Render.
3. Usa el endpoint `/verificar` para ejecutar la verificación.
