import time
from verificador import ejecutar_verificacion

if __name__ == "__main__":
    print("⏱️ Iniciando verificador en segundo plano cada 5 minutos...")
    while True:
        try:
            ejecutar_verificacion()
        except Exception as e:
            print("❌ Error en verificación:", e)
        time.sleep(60)  # 300 segundos = 5 minutos
