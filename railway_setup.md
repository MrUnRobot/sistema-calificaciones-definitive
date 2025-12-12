# Despliegue en Railway

## Variables de Entorno REQUERIDAS en Railway:
1. `PORT` - Automático de Railway
2. `MONGO_URL` - Tu conexión de MongoDB (Railway MongoDB o Atlas)
3. `FLASK_SECRET_KEY` - clave_secreta_para_sesiones (o una más segura)

## Para desarrollo local:
```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar
python app.py