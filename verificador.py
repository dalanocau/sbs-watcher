import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

TELEGRAM_TOKEN = "tu_token"
TELEGRAM_CHAT_ID = "tu_chat_id"
SPREADSHEET_NAME = "SBS_FECHAS"
SHEET_NAME = "Fechas"

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    try:
        r = requests.post(url, json=payload)
        r.raise_for_status()
        print("✅ Notificación enviada")
    except Exception as e:
        print("❌ Error enviando Telegram:", e)

def conectar_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).worksheet(SHEET_NAME)
    return sheet

def leer_fecha_actual(sheet):
    fecha_str = sheet.acell("B2").value.strip()
    return datetime.strptime(fecha_str, "%d/%m/%Y")

def obtener_fecha_objetivo(fecha_base):
    siguiente = fecha_base + timedelta(days=32)
    return siguiente.replace(day=1) - timedelta(days=1)

def existe_archivo_sbs(fecha_objetivo):
    return True  # Simulación

def actualizar_fecha(sheet, nueva_fecha):
    sheet.update_acell("B2", nueva_fecha.strftime("%d/%m/%Y"))

def ejecutar_verificacion():
    sheet = conectar_sheet()
    fecha_actual = leer_fecha_actual(sheet)
    fecha_objetivo = obtener_fecha_objetivo(fecha_actual)

    if existe_archivo_sbs(fecha_objetivo):
        actualizar_fecha(sheet, fecha_objetivo)
        enviar_telegram(f"📁 Nuevo archivo detectado para {fecha_objetivo.strftime('%B %Y')}")
    else:
        print("⏳ Aún no hay nueva actualización disponible.")
