import os
import time
import requests
from binance.client import Client

# 1. CONFIGURACIÓN DE CREDENCIALES
client = Client('', '')  # No requiere llaves para leer datos públicos

TELEGRAM_TOKEN = '8968451696:AAF_QGs61ZQLDGVmjhLsP_2GoK1J3mDFcA8'
TELEGRAM_CHAT_ID = '8737478796'

# 2. PARÁMETROS DEL RADAR PERSONALIZADOS (Ajusta estos valores a tu gusto)
LIMITE_SUBIDA_1H = 00.05  # Alerta si sube más de +300% en 1 hora
LIMITE_BAJADA_1H = 1.0   # Alerta si cae más de -50% en 1 hora

LIMITE_SUBIDA_24H = 500.0 # Alerta si sube más de +500% en 24 horas
LIMITE_BAJADA_24H = 70.0  # Alerta si cae más de -70% en 24 horas

INTERVALO_BASE = 60  # Revisión cada 1 minuto

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
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"✅ Mensaje enviado para {token}")
        else:
            print(f"❌ Error de Telegram: {response.text}")
    except Exception as e:
        print(f"Error enviando Telegram: {e}")

def ejecutar_radar_dual():
    print("🛸 Radar Dual de Futuros (Límites Separados) iniciado...")
    
    # IMPORTANTE: Cambia a 60 para medir 1 hora real cuando termines tus pruebas
    MAX_ELEMENTOS_1H = 60        
    MAX_ELEMENTOS_24H = 1440     
    
    while True:
        try:
            tickers_futuros = client.futures_ticker()
            for ticker in tickers_futuros:
                simbolo = ticker['symbol']
                if simbolo.endswith('USDT'):
                    precio_actual = float(ticker['lastPrice'])
                    
                    # --- EVALUACIÓN 1 HORA ---
                    if simbolo not in precios_1h: precios_1h[simbolo] = []
                    if len(precios_1h[simbolo]) >= MAX_ELEMENTOS_1H:
                        precio_viejo_1h = precios_1h[simbolo][0]
                        variacion_1h = ((precio_actual - precio_viejo_1h) / precio_viejo_1h) * 100
                        
                        # Lógica separada: Evalúa subidas o bajadas de forma independiente
                        if variacion_1h >= LIMITE_SUBIDA_1H or variacion_1h <= -LIMITE_BAJADA_1H:
                            enviar_alerta_telegram(simbolo, "1 Hora", variacion_1h, precio_actual)
                            precios_1h[simbolo].clear()  
                            
                    precios_1h[simbolo].append(precio_actual)
                    if len(precios_1h[simbolo]) > MAX_ELEMENTOS_1H: precios_1h[simbolo].pop(0)
                    
                    # --- EVALUACIÓN 24 HORAS ---
                    if simbolo not in precios_24h: precios_24h[simbolo] = []
                    if len(precios_24h[simbolo]) >= MAX_ELEMENTOS_24H:
                        precio_viejo_24h = precios_24h[simbolo][0]
                        variacion_24h = ((precio_actual - precio_viejo_24h) / precio_viejo_24h) * 100
                        
                        # Lógica separada para 24 horas
                        if variacion_24h >= LIMITE_SUBIDA_24H or variacion_24h <= -LIMITE_BAJADA_24H:
                            enviar_alerta_telegram(simbolo, "24 Horas", variacion_24h, precio_actual)
                            precios_24h[simbolo].clear()  
                            
                    precios_24h[simbolo].append(precio_actual)
                    if len(precios_24h[simbolo]) > MAX_ELEMENTOS_24H: precios_24h[simbolo].pop(0)
            print("⏳ Ciclo de escaneo completado.")
        except Exception as e:
            print(f"⚠️ Error: {e}")
        time.sleep(INTERVALO_BASE)

if __name__ == "__main__":
    ejecutar_radar_dual()
