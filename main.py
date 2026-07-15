import time
import requests
from binance.client import Client

# 1. CONFIGURACIÓN DE CREDENCIALES
client = Client('', '')  # Datos públicos de Binance

TELEGRAM_TOKEN = '8968451696:AAF_QGs61ZQLDGVmjhLsP_2GoK1J3mDFcA8'
TELEGRAM_CHAT_ID = '8737478796'

# 2. PARÁMETROS DEL RADAR EN PRODUCCIÓN
LIMITE_SUBIDA_1H = 300.0  
LIMITE_BAJADA_1H = 50.0   
LIMITE_SUBIDA_24H = 500.0 
LIMITE_BAJADA_24H = 70.0  
INTERVALO_BASE = 60  

precios_1h = {}   
precios_24h = {}  
ultimo_update_id = 0  

# NUEVA VARIABLE: Diccionario para guardar tus alarmas fijas
# Formato interno: {'BTCUSDT': [{'precio_objetivo': 66000.0, 'precio_inicial': 62000.0}]}
alarmas_personalizadas = {}

def enviar_alerta_telegram(token, temporalidad, variacion, precio_actual):
    url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
    icono = "🟢" if variacion > 0 else "🔴"
    direccion = "🚀 *EXPLOSIÓN AL ALZA (PUMP)*" if variacion > 0 else "📉 *COLAPSO A LA BAJA (DUMP)*"
    
    mensaje = (
        f"🚨 *ALERTA DE VOLATILIDAD EXTREMA* 🚨\n\n"
        f"🔔 *Activo:* #{token}\n"
        f"⏱️ *Temporalidad:* {temporalidad}\n"
        f"📊 *Movimiento:* {direccion}\n"
        f"📈 *Variación:* {icono} {variacion:.2f}%\n"
        f"💰 *Precio Actual:* ${precio_actual:,.4f}"
    )
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload)
    except: pass

def revisar_alarmas_fijas(simbolo, precio_actual):
    """Revisa si el precio cruzó alguna de las alertas programadas por el usuario"""
    if simbolo in alarmas_personalizadas:
        # Recorremos al revés para poder borrar elementos de la lista mientras iteramos
        for i in range(len(alarmas_personalizadas[simbolo]) - 1, -1, -1):
            alarma = alarmas_personalizadas[simbolo][i]
            precio_obj = alarma['precio_objetivo']
            precio_ini = alarma['precio_inicial']
            
            # Detectar si venía de abajo y subió, o si venía de arriba y cayó
            disparada = False
            if precio_ini <= precio_obj and precio_actual >= precio_obj:
                disparada = True
                direccion_flecha = "📈 ¡Cruzó al alza!"
            elif precio_ini >= precio_obj and precio_actual <= precio_obj:
                disparada = True
                direccion_flecha = "📉 ¡Cruzó a la baja!"
                
            if disparada:
                # Enviar notificación inmediata de precio alcanzado
                url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
                mensaje = (
                    f"🎯 *¡ALARMA DE PRECIO ALCANZADA!* 🎯\n\n"
                    f"🪙 *Activo:* #{simbolo}\n"
                    f"📌 *Precio Objetivo:* ${precio_obj:,.2f}\n"
                    f"💵 *Precio Actual:* ${precio_actual:,.2f}\n"
                    f"⚡ *Condición:* {direccion_flecha}"
                )
                try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"})
                except: pass
                
                # Borramos la alarma para que no vuelva a sonar infinitamente
                alarmas_personalizadas[simbolo].pop(i)

def revisar_comandos_unificado():
    global ultimo_update_id
    url_updates = f"https://telegram.org{TELEGRAM_TOKEN}/getUpdates"
    
    try:
        params = {"timeout": 0}
        if ultimo_update_id != 0: params["offset"] = ultimo_update_id + 1
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
                            # --- COMANDO 1: /PRECIO ---
                            if texto.startswith("/PRECIO"):
                                partes = texto.split()
                                if len(partes) > 1:
                                    token_solicitado = partes[1]
                                    if not token_solicitado.endswith("USDT"): token_solicitado += "USDT"
                                    try:
                                        ticker = client.futures_ticker(symbol=token_solicitado)
                                        precio = float(ticker['lastPrice'])
                                        var_24h = float(ticker['priceChangePercent'])
                                        icono = "🟢" if var_24h >= 0 else "🔴"
                                        respuesta = f"💰 *Precio de {token_solicitado}:*\n\n💵 `${precio:,.4f}`\n📊 *Var. Binance 24h:* {icono} {var_24h:.2f}%"
                                    except: respuesta = f"❌ Token *{token_solicitado}* no encontrado."
                                else: respuesta = "💡 Uso correcto: `/precio btc`"
                                
                                requests.post(f"{URL_BASE_TELEGRAM}/sendMessage" if 'URL_BASE_TELEGRAM' in locals() else f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": respuesta, "parse_mode": "Markdown"})
                            
                            # --- NUEVO COMANDO 2: /ALERTA (Ej: /alerta btc 66000) ---
                            elif texto.startswith("/ALERTA"):
                                partes = texto.split()
                                if len(partes) > 2:
                                    token_solicitado = partes[1]
                                    if not token_solicitado.endswith("USDT"): token_solicitado += "USDT"
                                    
                                    try:
                                        precio_objetivo = float(partes[2].replace(",", ""))
                                        # Consultamos el precio actual para saber si la alarma va hacia arriba o hacia abajo
                                        ticker = client.futures_ticker(symbol=token_solicitado)
                                        precio_actual = float(ticker['lastPrice'])
                                        
                                        if token_solicitado not in alarmas_personalizadas:
                                            alarmas_personalizadas[token_solicitado] = []
                                            
                                        alarmas_personalizadas[token_solicitado].append({
                                            'precio_objetivo': precio_objetivo,
                                            'precio_inicial': precio_actual
                                        })
                                        
                                        respuesta = (
                                            f"✅ *Alarma Programada*\n\n"
                                            f"🪙 *Activo:* #{token_solicitado}\n"
                                            f"🎯 *Avisar en:* ${precio_objetivo:,.2f}\n"
                                            f"💵 *Precio Actual:* ${precio_actual:,.2f}"
                                        )
                                    except:
                                        respuesta = "❌ Error al programar la alarma. Verifica el nombre del token y que el precio sea un número."
                                else:
                                    respuesta = "💡 Uso correcto: `/alerta btc 66000` o `/alerta sol 145.50`"
                                
                                requests.post(f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": respuesta, "parse_mode": "Markdown"})
    except: pass

def ejecutar_radar_dual():
    print("🛸 Radar Dual de Futuros con Alertas Fijas Iniciado...")
    MAX_ELEMENTOS_1H = 60        
    MAX_ELEMENTOS_24H = 1440     
    revisar_comandos_unificado()
    
    while True:
        try:
            tickers_futuros = client.futures_ticker()
            for ticker in tickers_futuros:
                simbolo = ticker['symbol']
                if simbolo.endswith('USDT'):
                    precio_actual = float(ticker['lastPrice'])
                    
                    # NUEVA COMPROBACIÓN: Evaluamos si el precio tocó alguna de tus alarmas guardadas
                    revisar_alarmas_fijas(simbolo, precio_actual)
                    
                    # --- EVALUACIÓN 1 HORA ---
                    if simbolo not in precios_1h: precios_1h[simbolo] = []
                    if len(precios_1h[simbolo]) >= MAX_ELEMENTOS_1H:
                        precio_viejo_1h = precios_1h[simbolo][0]
                        variacion_1h = ((precio_actual - precio_viejo_1h) / precio_viejo_1h) * 100
                        if variacion_1h >= LIMITE_SUBIDA_1H or variacion_1h <= -LIMITE_BAJADA_1H:
                            enviar_alerta_telegram(simbolo, "1 Hora", variacion_1h, precio_actual)
                            precios_1h[simbolo].pop(0)  
                    precios_1h[simbolo].append(precio_actual)
                    if len(precios_1h[simbolo]) > MAX_ELEMENTOS_1H: precios_1h[simbolo].pop(0)
                    
                    # --- EVALUACIÓN 24 HORAS ---
                    if simbolo not in precios_24h: precios_24h[simbolo] = []
                    if len(precios_24h[simbolo]) >= MAX_ELEMENTOS_24H:
                        precio_viejo_24h = precios_24h[simbolo][0]
                        variacion_24h = ((precio_actual - precio_viejo_24h) / precio_viejo_24h) * 100
                        if variacion_24h >= LIMITE_SUBIDA_24H
                        or variacion_24h <= -LIMITE_BAJADA_24H:
                            enviar_alerta_telegram(simbolo, "24 Horas", variacion_24h, precio_actual)
                            precios_24h[simbolo].pop(0)
                    precios_24h[simbolo].append(precio_actual)
                    if len(precios_24h[simbolo]) > MAX_ELEMENTOS_24H: precios_24h[simbolo].pop(0)
        print("⏳ Ciclo de escaneo completado con éxito.")
        except Exception as e:
            print(f"⚠️ Error: {e}")
            for _ in range(INTERVALO_BASE):
                revisar_comandos_unificado()
                time.sleep(1)
                if name == "main":
                    ejecutar_radar_dual()
