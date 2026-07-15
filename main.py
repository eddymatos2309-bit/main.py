import os
import time
import requests
from datetime import datetime
from binance.client import Client

# 1. CONFIGURACIÓN DE CREDENCIALES
client = Client('', '')  # Datos públicos de Binance

TELEGRAM_TOKEN = '8968451696:AAF_QGs61ZQLDGVmjhLsP_2GoK1J3mDFcA8'
TELEGRAM_CHAT_ID = '8737478796'

URL_BASE_TELEGRAM = f"https://telegram.org{TELEGRAM_TOKEN}"

# 2. PARÁMETROS DEL RADAR
LIMITE_SUBIDA_1H = 300.0  
LIMITE_BAJADA_1H = 50.0   
LIMITE_SUBIDA_24H = 500.0 
LIMITE_BAJADA_24H = 70.0  
INTERVALO_BASE = 60  

precios_1h = {}   
precios_24h = {}  
ultimo_update_id = 0  

def guardar_en_historial(token, temporalidad, variacion, precio):
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tipo = "PUMP" if variacion > 0 else "DUMP"
    linea = f"[{ahora}] {tipo} | {token} | {temporalidad} | Variación: {variacion:.2f}% | Precio: ${precio:,.4f}\n"
    try:
        with open("alertas_historial.txt", "a", encoding="utf-8") as f:
            f.write(linea)
        print(f"💾 Alerta registrada en historial para {token}")
    except Exception as e:
        print(f"Error al escribir en historial: {e}")

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
            guardar_en_historial(token, temporalidad, variacion, precio_actual)
    except Exception as e:
        print(f"Error enviando Telegram: {e}")

def revisar_comandos_unificado():
    """Revisa los comandos pendientes sin bloquear el script y de forma lineal"""
    global ultimo_update_id
    url_updates = f"{URL_BASE_TELEGRAM}/getUpdates"
    
    try:
        # Petición ultra rápida (timeout=0) para que sea instantánea la respuesta
        params = {"offset": ultimo_update_id + 1, "timeout": 0}
        response_raw = requests.get(url_updates, params=params)
        
        if response_raw.status_code == 200 and "application/json" in response_raw.headers.get("Content-Type", ""):
            response = response_raw.json()
            
            if "result" in response:
                for update in response["result"]:
                    ultimo_update_id = update["update_id"]
                    
                    message_data = update.get("message")
                    if message_data and "text" in message_data:
                        texto = message_data["text"].strip().upper()
                        chat_id_remitente = str(message_data["chat"].get("id"))
                        
                        if chat_id_remitente == TELEGRAM_CHAT_ID:
                            if texto.startswith("/PRECIO"):
                                partes = texto.split()
                                if len(partes) > 1:
                                    # Tomamos la segunda palabra limpia (el símbolo)
                                    token_solicitado = partes[1]
                                    
                                    if not token_solicitado.endswith("USDT"):
                                        token_solicitado += "USDT"
                                        
                                    try:
                                        ticker = client.futures_ticker(symbol=token_solicitado)
                                        precio = float(ticker['lastPrice'])
                                        var_24h = float(ticker['priceChangePercent'])
                                        icono = "🟢" if var_24h >= 0 else "🔴"
                                        respuesta = f"💰 *Precio de {token_solicitado}:*\n\n💵 `${precio:,.4f}`\n📊 *Var. Binance 24h:* {icono} {var_24h:.2f}%"
                                    except Exception:
                                        respuesta = f"❌ El token *{token_solicitado}* no fue encontrado en Binance Futuros."
                                else:
                                    respuesta = "💡 Uso correcto: `/precio btc`"
                                    
                                url_send = f"{URL_BASE_TELEGRAM}/sendMessage"
                                requests.post(url_send, json={"chat_id": TELEGRAM_CHAT_ID, "text": respuesta, "parse_mode": "Markdown"})
    except Exception as e:
        # Silenciamos fallas menores de red de Telegram para no interrumpir el radar
        pass

def ejecutar_radar_dual():
    print("🛸 Radar Unificado de Futuros iniciado en Railway (Comandos Interactivos Activos)...")
    MAX_ELEMENTOS_1H = 60        
    MAX_ELEMENTOS_24H = 1440     
    
    while True:
        # Escaneamos el mercado de Binance Futuros
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
                        if variacion_24h >= LIMITE_SUBIDA_24H or variacion_24h <= -LIMITE_BAJADA_24H:
                            enviar_alerta_telegram(simbolo, "24 Horas", variacion_24h, precio_actual)
                            precios_24h[simbolo].clear()  
                    precios_24h[simbolo].append(precio_actual)
                    if len(precios_24h[simbolo]) > MAX_ELEMENTOS_24H: precios_24h[simbolo].pop(0)
            print("⏳ Ciclo de escaneo completado.")
        except Exception as e:
            print(f"⚠️ Error en ciclo Binance: {e}")
            
        # MEJORA CLAVE: En lugar de congelar por 60 segundos completos,
        # dividimos el tiempo para revisar Telegram una vez por segundo.
        for _ in range(INTERVALO_BASE):
            revisar_comandos_unificado()
            time.sleep(1)

if __name__ == "__main__":
    ejecutar_radar_dual()
