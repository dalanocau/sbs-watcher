from flask import Flask
from verificador import ejecutar_verificacion

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Servicio de verificación activo."

@app.route('/verificar')
def verificar():
    ejecutar_verificacion()
    return "✅ Verificación ejecutada."
