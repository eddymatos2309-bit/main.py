import os
import time
import requests
import threading
from datetime import datetime
from binance.client import Client

# 1. CONFIGURACIÓN DE CREDENCIALES
client = Client('', '')  # Datos públicos

TELEGRAM_TOKEN = '8968451696:AAF_QGs61ZQLDGVmjhLsP_2GoK1J3mDFcA8'
TELEGRAM_CHAT_ID = '8737478796'

# 2. PARÁMETROS DEL RADAR
LIMITE_SUBIDA_1H = 400.0  
LIMITE_BAJADA_1H = 80.0   
LIMITE_SUBIDA_24H = 600.0 
LIMITE_BAJADA_24H = 85.0  
INTERVALO_BASE = 60  

precios_1h = {}   
precios_24h = {}  
ultimo_update_id = 0  # Para controlar los mensajes leídos de Telegram

def guardar_en_historial(token, temporalidad, variacion, precio):
    """Guarda un registro de la alerta en un archivo de texto con fecha y hora"""
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
        # Ejecutamos la función de guardado local
        guardar_en_historial(token, temporalidad, variacion, precio_actual)
    except Exception as e:
        print(f"Error enviando Telegram: {e}")

def escuchar_comandos_telegram():
    """Función secundaria que corre en segundo plano esperando tus mensajes"""
    global ultimo_update_id
    url_updates = f"https://telegram.org{TELEGRAM_TOKEN}/getUpdates"
    print("🤖 Bot de comandos interactivos activado...")
    
    while True:
        try:
            # Pedimos a Telegram los nuevos mensajes
            params = {"offset": ultimo_update_id + 1, "timeout": 10}
            response = requests.get(url_updates, params=params).json()
            
            if "result" in response:
                for update in response["result"]:
                    ultimo_update_id = update["update_id"]
                    
                    if "message" in update and "text" in update["message"]:
                        texto = update["message"]["text"].strip().upper()
                        chat_id_remitente = str(update["message"]["chat_id"])
                        
                        # Seguridad: Solo responderte a ti
                        if chat_id_remitente == TELEGRAM_CHAT_ID:
                            # Comando /precio
                            if texto.startswith("/PRECIO"):
                                partes = texto.split()
                                if len(partes) > 1:
                                    token_solicitado = partes[1]
                                    # Aseguramos que termine en USDT si no lo escribiste
                                    if not token_solicitado.endswith("USDT"):
                                        token_solicitado += "USDT"
                                        
                                    try:
                                        ticker = client.futures_ticker(symbol=token_solicitado)
                                        precio = float(ticker['lastPrice'])
                                        var_24h = float(ticker['priceChangePercent'])
                                        icono = "🟢" if var_24h >= 0 else "🔴"
                                        
                                        respuesta = (
                                            f"💰 *Precio de {token_solicitado}:*\n"
                                            f"💵 `${precio:,.4f}`\n"
                                            f"📊 *Var. Binance 24h:* {icono} {var_24h:.2f}%"
                                        )
                                    except:
                                        respuesta = f"❌ El token *{token_solicitado}* no fue encontrado en Binance Futuros. Revisa la ortografía."
                                else:
                                    respuesta = "💡 Uso correcto: `/precio btc` o `/precio solusdt`"
                                    
                                # Enviar respuesta del comando
                                url_send = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
                                requests.post(url_send, json={"chat_id": TELEGRAM_CHAT_ID, "text": respuesta, "parse_mode": "Markdown"})
                                
        except Exception as e:
            print(f"Error en bot de comandos: {e}")
        time.sleep(1)

def ejecutar_radar_dual():
    print("🛸 Radar Dual de Futuros iniciado...")
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
                        if variacion_1h >= LIMITE_SUBIDA_1H or variacion_1h <= -LIMITE_BAJADA_1H:
                            enviar_alerta_telegram(simbolo, "1 Hora", variacion_1h, precio_actual)
                            precios_1h[simbolo].clear()  
                    precios_1h[simbolo].append(precio_actual)
                    if len(precios_1h[simbolo]) > MAX_ELEMENTOS_1H: precios_1h[simbolo].pop(0)
                    
                    # --- EVALUACIÓN 24 HORAS ---
                    if simbolo not in precios_24h: precios_24h[simbolo] = []
                    if len(precios_24h[simbolo]) >= MAX_ELEMENTOS_24H:
                        precio_viejo_24h = precios_24h[simbolo][0]
                        variacion_24h = ((precio_actual - precio_viejo_24h) / precio_24h[simbolo][0]) * 100
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
    # Iniciar el hilo del Bot de Comandos de Telegram en segundo plano
    hilo_bot = threading.Thread(target=escuchar_comandos_telegram, daemon=True)
    hilo_bot.start()
    
    # Iniciar el Radar Principal de Binance en el hilo principal
    ejecutar_radar_dual()
