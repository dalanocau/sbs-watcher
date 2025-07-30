import os
import threading
import time
from datetime import datetime
from pytz import timezone

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from flask import Flask, render_template_string

# ------------------- CONFIGURACIÓN -------------------
CRED_FILE = "credenciales.json"  # 🔹 Sube este archivo a Render o usa variables de entorno
SHEET_NAME = "verificacion_fechas"

# Configuración de Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # 🔹 Ponlo en Render → Environment Variables
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

codigos_archivo = {
    "BANCOS": "B-2201",
    "FINANCIERAS": "B-3101",
    "CMACS": "C-1101",
    "CRACS": "C-2101",
    "EMPRESAS_CREDITO": "C-4103",
    "DEPOSITOS_CAJA": "C-1245",
    "DEPOSITOS_FINANCIERAS": "B-3231",
    "COLOCACIONES_EC": "C-4223"
}

abreviaturas = {
    1: ('Enero', 'en'), 2: ('Febrero', 'fe'), 3: ('Marzo', 'ma'), 4: ('Abril', 'ab'),
    5: ('Mayo', 'my'), 6: ('Junio', 'jn'), 7: ('Julio', 'jl'), 8: ('Agosto', 'ag'),
    9: ('Setiembre', 'se'), 10: ('Octubre', 'oc'), 11: ('Noviembre', 'no'), 12: ('Diciembre', 'di')
}

# ------------------- VARIABLES GLOBALES -------------------
ultimo_resultado = {}
ultimo_envio = "Nunca"

# ------------------- FUNCIONES -------------------
def conectar_google_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CRED_FILE, scope)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

def leer_fechas_anteriores(sheet):
    data = sheet.get_all_records()
    return {row['ENTIDAD']: row['FECHA_ANTERIOR'] for row in data}

def actualizar_fechas(sheet, nuevas_fechas):
    data = sheet.get_all_records()
    for i, row in enumerate(data, start=2):
        entidad = row['ENTIDAD']
        nueva_fecha = nuevas_fechas.get(entidad)
        if nueva_fecha:
            sheet.update_cell(i, 2, nueva_fecha)

def enviar_telegram(mensaje):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ No hay configuración de Telegram")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    try:
        requests.post(url, json=payload)
        print(f"📲 Telegram enviado: {mensaje}")
    except Exception as e:
        print(f"❌ Error enviando Telegram: {e}")

def obtener_mes_siguiente(fecha_str):
    from calendar import monthrange
    try:
        fecha = datetime.strptime(fecha_str, "%d/%m/%Y")
        anio = fecha.year
        mes = fecha.month + 1
        if mes > 12:
            mes = 1
            anio += 1
        dia_final = monthrange(anio, mes)[1]
        return f"{dia_final:02d}/{mes:02d}/{anio}", anio, mes
    except:
        return None, None, None

def verificar_archivo(anio, mes, entidad):
    mes_nombre, mes_abr = abreviaturas[mes]
    codigo = codigos_archivo[entidad]
    url = f"https://intranet2.sbs.gob.pe/estadistica/financiera/{anio}/{mes_nombre}/"
    archivo = f"{codigo}-{mes_abr}{anio}.xls"
    full_url = f"{url}{archivo}"
    try:
        response = requests.head(full_url, timeout=3)
        return response.status_code == 200
    except:
        return None

def es_fecha_valida(fecha):
    try:
        datetime.strptime(fecha, "%d/%m/%Y")
        return True
    except:
        return False

def check_website_changes():
    global ultimo_resultado, ultimo_envio
    sheet = conectar_google_sheet()
    fechas_anteriores = leer_fechas_anteriores(sheet)
    fechas_nuevas = {}

    for entidad, fecha_actual in fechas_anteriores.items():
        if not es_fecha_valida(fecha_actual):
            fechas_nuevas[entidad] = fecha_actual
            continue

        siguiente_fecha_str, anio, mes = obtener_mes_siguiente(fecha_actual)
        if not (anio and mes):
            continue

        existe = verificar_archivo(anio, mes, entidad)
        if existe:
            msg = f"🟡 Nuevo archivo SBS para {entidad}: {siguiente_fecha_str}"
            enviar_telegram(msg)
            fechas_nuevas[entidad] = siguiente_fecha_str
        else:
            fechas_nuevas[entidad] = fecha_actual

    actualizar_fechas(sheet, fechas_nuevas)
    ultimo_resultado = fechas_nuevas
    ultimo_envio = datetime.now(timezone('America/Lima')).strftime('%Y-%m-%d %H:%M:%S %Z')
    print(f"✅ Verificación completada: {ultimo_envio}")

def ciclo_verificacion():
    while True:
        try:
            check_website_changes()
        except Exception as e:
            print(f"❌ Error en verificación: {e}")
        time.sleep(1800)  # 30 minutos

# ------------------- SERVIDOR WEB -------------------
app = Flask(__name__)

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Verificación SBS</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
<div class="container py-4">
    <h1 class="text-center mb-4">📊 Verificación de Archivos SBS</h1>
    <p class="text-center">Última verificación: <strong>{{ ultimo_envio }}</strong></p>
    <table class="table table-bordered table-hover bg-white shadow-sm">
        <thead class="table-primary">
            <tr>
                <th>Entidad</th>
                <th>Última Fecha</th>
            </tr>
        </thead>
        <tbody>
            {% for entidad, fecha in datos.items() %}
            <tr>
                <td>{{ entidad }}</td>
                <td>{{ fecha }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(TEMPLATE, datos=ultimo_resultado, ultimo_envio=ultimo_envio)

if __name__ == "__main__":
    # Iniciar el ciclo de verificación en segundo plano
    threading.Thread(target=ciclo_verificacion, daemon=True).start()
    # Servidor para Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
