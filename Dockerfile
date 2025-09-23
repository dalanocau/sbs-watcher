FROM python:3.11-slim

# Carpeta de trabajo dentro del contenedor
WORKDIR /app

# Copiar dependencias e instalarlas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Variable de entorno para Cloud Run
ENV PORT 8080

# Comando de arranque: gunicorn busca la variable app dentro de app.py
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app
