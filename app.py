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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
