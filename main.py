import os
import time
import requests
from binance.client import Client

# 1. CONFIGURACIÓN DE CREDENCIALES (Cargadas de forma segura desde la nube)
client = Client('', '')  # No requiere llaves para leer datos públicos

TELEGRAM_TOKEN = os.environ.get('8968451696:AAF_QGs61ZQLDGVmjhLsP_2GoK1J3mDFcA8')
TELEGRAM_CHAT_ID = os.environ.get('8737478796')

# 2. PARÁMETROS DEL RADAR
LIMITE_1H = 10.0   
LIMITE_24H = 50.0  
INTERVALO_BASE = 60  

precios_1h = {}   
precios_24h = {}  

def enviar_alerta_telegram(token, temporalidad, variacion, precio_actual):
    url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
    
    if variacion > 0:
        direccion = "🚀 *EXPLOSIÓN AL ALZA (PUMP)*"
        icono = "🟢"
    else:
        direccion = "📉 *COLAPSO A LA BAJA (DUMP)*"
        icono = "🔴"
    
    mensaje = (
        f"🚨 *ALERTA DE VOLATILIDAD EXTREMA* 🚨\n\n"
        f"🔔 *Activo:* #{token}\n"
        f"⏱️ *Temporalidad:* {temporalidad}\n"
        f"📊 *Movimiento:* {direccion}\n"
        f"📈 *Variación:* {icono} {variacion:.2f}%\n"
        f"💰 *Precio Actual:* ${precio_actual:,.4f}"
    )
    
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error enviando Telegram: {e}")

def ejecutar_radar_dual():
    print("🛸 Radar Dual de Futuros iniciado en Render...")
    MAX_ELEMENTOS_1H = 60        
    MAX_ELEMENTOS_24H = 1440     
    
    while True:
        try:
            tickers_futuros = client.futures_ticker()
            for ticker in tickers_futuros:
                simbolo = ticker['symbol']
                if simbolo.endswith('USDT'):
                    precio_actual = float(ticker['lastPrice'])
                    
                    # Evaluación 1 Hora
                    if simbolo not in precios_1h: precios_1h[simbolo] = []
                    if len(precios_1h[simbolo]) >= MAX_ELEMENTOS_1H:
                        precio_viejo_1h = precios_1h[simbolo][0]
                        variacion_1h = ((precio_actual - precio_viejo_1h) / precio_viejo_1h) * 100
                        if abs(variacion_1h) >= LIMITE_1H:
                            enviar_alerta_telegram(simbolo, "1 Hora", variacion_1h, precio_actual)
                            precios_1h[simbolo] = [] 
                    precios_1h[simbolo].append(precio_actual)
                    if len(precios_1h[simbolo]) > MAX_ELEMENTOS_1H: precios_1h[simbolo].pop(0)
                    
                    # Evaluación 24 Horas
                    if simbolo not in precios_24h: precios_24h[simbolo] = []
                    if len(precios_24h[simbolo]) >= MAX_ELEMENTOS_24H:
                        precio_viejo_24h = precios_24h[simbolo][0]
                        variacion_24h = ((precio_actual - precio_viejo_24h) / precio_viejo_24h) * 100
                        if abs(variacion_24h) >= LIMITE_24H:
                            enviar_alerta_telegram(simbolo, "24 Horas", variacion_24h, precio_actual)
                            precios_24h[simbolo] = []
                    precios_24h[simbolo].append(precio_actual)
                    if len(precios_24h[simbolo]) > MAX_ELEMENTOS_24H: precios_24h[simbolo].pop(0)
            print("⏳ Ciclo de escaneo completado.")
        except Exception as e:
            print(f"⚠️ Error: {e}")
        time.sleep(INTERVALO_BASE)

if __name__ == "__main__":
    ejecutar_radar_dual()
