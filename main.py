from flask import Flask
from threading import Thread
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from calendar import monthrange
import requests
import time
import os
import json
from twilio.rest import Client

# --- CONFIGURACIÓN ---
SHEET_NAME = "verificacion_fechas"

# Twilio
TWILIO_SID = "AC27f9a63a992b1f8ddc57b894aad851fe"
TWILIO_TOKEN = "ac82f09f391afe28b001dd5cc513510b"
TWILIO_FROM = "whatsapp:+14155238886"
WHATSAPP_TO = "whatsapp:+51912313398"  # ← Tu número de WhatsApp

# Diccionario de códigos SBS
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

# Meses
abreviaturas = {
    1: ('Enero', 'en'), 2: ('Febrero', 'fe'), 3: ('Marzo', 'ma'), 4: ('Abril', 'ab'),
    5: ('Mayo', 'my'), 6: ('Junio', 'jn'), 7: ('Julio', 'jl'), 8: ('Agosto', 'ag'),
    9: ('Setiembre', 'se'), 10: ('Octubre', 'oc'), 11: ('Noviembre', 'no'), 12: ('Diciembre', 'di')
}

# Estado actual para el endpoint
estado_actual = {
    "ultima_revision": "No se ha hecho ninguna revisión aún",
    "fechas": {}
}

# --- SERVIDOR FLASK SOLO PARA CONSULTA ---
app = Flask(__name__)

@app.route("/")
def home():
    respuesta = f"✅ SBS Watcher activo\n"
    respuesta += f"🔍 Última revisión: {estado_actual['ultima_revision']}\n"
    respuesta += "📅 Fechas actuales:\n"
    for entidad, fecha in estado_actual['fechas'].items():
        respuesta += f"- {entidad}: {fecha}\n"
    return "<pre>" + respuesta + "</pre>"

def run_web():
    app.run(host="0.0.0.0", port=8080)

# --- GOOGLE SHEETS ---
def conectar_google_sheet():
    try:
        creds_json = os.getenv('GOOGLE_CRED_JSON')
        if not creds_json:
            raise Exception("⚠️ GOOGLE_CRED_JSON no está configurado en las variables de entorno.")
        creds_dict = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        print("✅ Conectado a Google Sheets correctamente.")
        return client.open(SHEET_NAME).sheet1
    except Exception as e:
        print(f"❌ Error al conectar con Google Sheets: {e}")
        raise

def leer_fechas_anteriores(sheet):
    try:
        data = sheet.get_all_records()
        return {row['ENTIDAD']: row['FECHA_ANTERIOR'] for row in data}
    except Exception as e:
        print(f"❌ Error al leer fechas anteriores: {e}")
        return {}

def actualizar_fecha(sheet, entidad, nueva_fecha):
    try:
        data = sheet.get_all_records()
        for i, row in enumerate(data, start=2):
            if row['ENTIDAD'] == entidad:
                sheet.update_cell(i, 2, nueva_fecha)
                print(f"✅ Fecha actualizada en Sheets para {entidad}: {nueva_fecha}")
                break
    except Exception as e:
        print(f"❌ Error al actualizar fecha en Sheets: {e}")

# --- NOTIFICACIÓN POR WHATSAPP ---
def enviar_notificacion(entidad, anterior, nueva):
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        body = f"📢 Cambio detectado en {entidad}:\n{anterior} → {nueva}"
        message = client.messages.create(
            body=body,
            from_=TWILIO_FROM,
            to=WHATSAPP_TO
        )
        print(f"📲 WhatsApp enviado: {message.sid}")
    except Exception as e:
        print(f"❌ Error al enviar WhatsApp: {e}")

# --- FUNCIONES DE VERIFICACIÓN ---
def verificar_archivo(anio, mes, entidad):
    mes_nombre, mes_abr = abreviaturas[mes]
    codigo = codigos_archivo[entidad]
    url = f"https://intranet2.sbs.gob.pe/estadistica/financiera/{anio}/{mes_nombre}/"
    archivo = f"{codigo}-{mes_abr}{anio}.xls"
    try:
        response = requests.head(f"{url}{archivo}", timeout=10)
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al verificar archivo para {entidad}: {e}")
        return None

def obtener_mes_siguiente(fecha_str):
    fecha = datetime.strptime(fecha_str, "%d/%m/%Y")
    anio = fecha.year + 1 if fecha.month == 12 else fecha.year
    mes = 1 if fecha.month == 12 else fecha.month + 1
    return anio, mes

def verificar_cambios():
    global estado_actual
    try:
        sheet = conectar_google_sheet()
        fechas_previas = leer_fechas_anteriores(sheet)

        estado_actual["ultima_revision"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        estado_actual["fechas"] = fechas_previas

        for entidad, fecha_prev in fechas_previas.items():
            if fecha_prev == "Sin archivos disponibles":
                continue

            anio, mes = obtener_mes_siguiente(fecha_prev)
            existe = verificar_archivo(anio, mes, entidad)

            if existe:
                dia_max = monthrange(anio, mes)[1]
                nueva_fecha = f"{dia_max:02d}/{mes:02d}/{anio}"
                print(f"🟢 ¡Nuevo mes detectado para {entidad}! {fecha_prev} → {nueva_fecha}")
                actualizar_fecha(sheet, entidad, nueva_fecha)
                enviar_notificacion(entidad, fecha_prev, nueva_fecha)
            else:
                print(f"🔍 {entidad}: sin cambios (última: {fecha_prev})")
    except Exception as e:
        print(f"❌ Error en verificar cambios: {e}")

# --- LOOP PRINCIPAL ---
def iniciar_verificador():
    while True:
        print("⏳ Verificando cambios en SBS...")
        try:
            verificar_cambios()
        except Exception as e:
            print(f"❌ Error en el ciclo principal: {e}")
        print("🕒 Próxima verificación en 1 hora...")
        time.sleep(3600)

if __name__ == "__main__":
    Thread(target=run_web).start()  # Servir Flask
    iniciar_verificador()
