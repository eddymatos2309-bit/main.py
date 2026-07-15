import time
import requests
from binance.client import Client

# 1. CONFIGURACIÓN DE CREDENCIALES
client = Client('', '')  # Datos públicos de Binance

TELEGRAM_TOKEN = '8968451696:AAF_QGs61ZQLDGVmjhLsP_2GoK1J3mDFcA8'
TELEGRAM_CHAT_ID = '8737478796'

URL_BASE_TELEGRAM = f"https://telegram.org{TELEGRAM_TOKEN}"

# 2. PARÁMETROS DEL RADAR (Valores muy bajos para forzar las alertas de inmediato)
LIMITE_SUBIDA_1H = 0.01  
LIMITE_BAJADA_1H = 0.01   
LIMITE_SUBIDA_24H = 50.0 
LIMITE_BAJADA_24H = 50.0  
INTERVALO_BASE = 60  # Escaneo cada 1 minuto

precios_1h = {}   
precios_24h = {}  

def enviar_alerta_telegram(token, temporalidad, variacion, precio_actual):
    url = f"{URL_BASE_TELEGRAM}/sendMessage"
    
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
    except Exception as e:
        print(f"Error enviando Telegram: {e}")

def ejecutar_radar_dual():
    print("🛸 Radar Dual Aislado de Futuros iniciado en Railway...")
    
    # Configuramos el historial para que guarde solo 2 minutos (Prueba rápida)
    MAX_ELEMENTOS_1H = 2        
    MAX_ELEMENTOS_24H = 1440     
    
    while True:
        try:
            tickers_futuros = client.futures_ticker()
            for ticker in tickers_futuros:
                simbolo = ticker['symbol']
                if simbolo.endswith('USDT'):
                    precio_actual = float(ticker['lastPrice'])
                    
                    # --- EVALUACIÓN 1 HORA (En esta prueba mide 2 minutos) ---
                    if simbolo not in precios_1h: 
                        precios_1h[simbolo] = []
                    
                    if len(precios_1h[simbolo]) >= MAX_ELEMENTOS_1H:
                        # Extraemos el precio viejo usando el índice [0] de forma segura
                        precio_viejo_1h = precios_1h[simbolo][0]
                        variacion_1h = ((precio_actual - precio_viejo_1h) / precio_viejo_1h) * 100
                        
                        if variacion_1h >= LIMITE_SUBIDA_1H or variacion_1h <= -LIMITE_BAJADA_1H:
                            enviar_alerta_telegram(simbolo, "1 Hora (Prueba)", variacion_1h, precio_actual)
                            precios_1h[simbolo].clear()  
                    
                    precios_1h[simbolo].append(precio_actual)
                    if len(precios_1h[simbolo]) > MAX_ELEMENTOS_1H: 
                        precios_1h[simbolo].pop(0)
                    
                    # --- EVALUACIÓN 24 HORAS ---
                    if simbolo not in precios_24h: 
                        precios_24h[simbolo] = []
                    
                    if len(precios_24h[simbolo]) >= MAX_ELEMENTOS_24H:
                        precio_viejo_24h = precios_24h[simbolo][0]
                        variacion_24h = ((precio_actual - precio_viejo_24h) / precio_viejo_24h) * 100
                        
                        if variacion_24h >= LIMITE_SUBIDA_24H or variacion_24h <= -LIMITE_BAJADA_24H:
                            enviar_alerta_telegram(simbolo, "24 Horas", variacion_24h, precio_actual)
                            precios_24h[simbolo].clear()  
                    
                    precios_24h[simbolo].append(precio_actual)
                    if len(precios_24h[simbolo]) > MAX_ELEMENTOS_24H: 
                        precios_24h[simbolo].pop(0)
                        
            print("⏳ Ciclo de escaneo completado con éxito.")
        except Exception as e:
            print(f"⚠️ Error en ciclo Binance: {e}")
            
        time.sleep(INTERVALO_BASE)

if __name__ == "__main__":
    ejecutar_radar_dual()
