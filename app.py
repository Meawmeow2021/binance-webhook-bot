from flask import Flask, request, jsonify
from binance.client import Client
from telegram import Bot
import os
import asyncio
import logging

# กำหนดค่า Logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# ดึงค่า API Keys/Tokens จาก Environment Variables (แนะนำอย่างยิ่ง!)
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
# สำหรับ Authentication ของ Webhook จาก TradingView
WEBHOOK_USERNAME = os.getenv('WEBHOOK_USERNAME')
WEBHOOK_PASSWORD = os.getenv('WEBHOOK_PASSWORD')

# ตรวจสอบว่า Environment Variables ถูกตั้งค่าหรือไม่
if not all([BINANCE_API_KEY, BINANCE_API_SECRET, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, WEBHOOK_USERNAME, WEBHOOK_PASSWORD]):
    logging.error("One or more environment variables are not set. Please check BINANCE_API_KEY, BINANCE_API_SECRET, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, WEBHOOK_USERNAME, WEBHOOK_PASSWORD.")
    # คุณอาจจะต้อง exit() หรือ raise an error ตรงนี้หากต้องการให้บอทหยุดทำงานทันที
    # สำหรับการพัฒนา อาจจะใช้ค่า default ชั่วคราว แต่ไม่แนะนำใน Production
    # BINANCE_API_KEY = "YOUR_BINANCE_API_KEY"
    # BINANCE_API_SECRET = "YOUR_BINANCE_API_SECRET"
    # ...

binance_client = None
telegram_bot = None

try:
    if BINANCE_API_KEY and BINANCE_API_SECRET:
        binance_client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
        logging.info("Binance client initialized.")
    else:
        logging.warning("Binance API keys not set. Trading functions will be disabled.")

    if TELEGRAM_BOT_TOKEN:
        telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)
        logging.info("Telegram bot initialized.")
    else:
        logging.warning("Telegram bot token not set. Telegram notifications will be disabled.")

except Exception as e:
    logging.error(f"Error initializing clients: {e}")

# ฟังก์ชันสำหรับส่งข้อความ Telegram (ใช้ asyncio เพื่อไม่ให้บล็อก Flask app)
async def send_telegram_message(message):
    if telegram_bot and TELEGRAM_CHAT_ID:
        try:
            await telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
            logging.info(f"Telegram message sent: {message}")
        except Exception as e:
            logging.error(f"Error sending Telegram message: {e}")
    else:
        logging.warning("Telegram bot not initialized or CHAT_ID not set. Cannot send message.")

# ฟังก์ชันสำหรับส่งคำสั่งเทรดไป Binance
async def place_binance_order(symbol, side, usdt_amount):
    if not binance_client:
        logging.error("Binance client not initialized. Cannot place order.")
        return False, "Binance client not initialized."

    try:
        # ตรวจสอบราคาปัจจุบันเพื่อคำนวณจำนวนเหรียญ
        info = binance_client.get_symbol_info(symbol)
        if not info:
            logging.error(f"Could not get symbol info for {symbol}")
            return False, f"Could not get symbol info for {symbol}"

        # สมมติว่า base asset เป็น USDT และ quote asset เป็นเหรียญที่คุณต้องการซื้อ/ขาย
        # เช่น สำหรับ BTCUSDT, BTC คือ base, USDT คือ quote
        
        # ตรวจสอบจำนวนเงิน USDT ที่มีอยู่ (ถ้าเป็นคำสั่งซื้อ)
        if side == 'BUY':
            account_info = binance_client.get_account()
            usdt_balance = float(next((item for item in account_info['balances'] if item['asset'] == 'USDT'), {}).get('free', '0'))
            if usdt_amount > usdt_balance:
                logging.warning(f"Insufficient USDT balance for BUY order. Requested: {usdt_amount}, Available: {usdt_balance}")
                await send_telegram_message(f"🚨 ALERT: Insufficient USDT for {side} {symbol}! Req: {usdt_amount}, Avail: {usdt_balance}")
                return False, "Insufficient USDT balance."

        # สำหรับ Market Order
        order_type = Client.ORDER_TYPE_MARKET
        
        # คำนวณปริมาณที่จะซื้อ/ขาย (quantity)
        # นี่คือส่วนที่ซับซ้อนและต้องจัดการเรื่อง MinNotional, StepSize, MinQuantity ของ Binance
        # ตัวอย่างนี้เป็นแบบง่ายๆ อาจต้องปรับให้ซับซ้อนขึ้น
        
        # ดึงราคาเฉลี่ยปัจจุบัน
        ticker = binance_client.get_avg_price(symbol=symbol)
        current_price = float(ticker['price'])
        
        # คำนวณ quantity โดยใช้ usdt_amount
        # Quantity = usdt_amount / current_price
        quantity = usdt_amount / current_price 
        
        # ตรวจสอบและปรับให้เข้ากับข้อกำหนดของ Binance (filters)
        # ส่วนนี้ควรจะจัดการด้วยความระมัดระวังและดึง symbol_info เพื่อตรวจสอบ filters
        # สำหรับตัวอย่างนี้ จะไม่ใส่รายละเอียดลึกในเรื่อง filters
        
        # คุณควรตรวจสอบ filters สำหรับ symbol_info['filters']
        # ตัวอย่าง:
        # for f in info['filters']:
        #     if f['filterType'] == 'LOT_SIZE':
        #         min_qty = float(f['minQty'])
        #         step_size = float(f['stepSize'])
        #         quantity = max(min_qty, round(quantity / step_size) * step_size) # ปรับให้เป็น step_size
        #     if f['filterType'] == 'MIN_NOTIONAL':
        #         min_notional = float(f['minNotional'])
        #         if usdt_amount < min_notional:
        #             logging.warning(f"Order notional ({usdt_amount}) less than minimum notional ({min_notional}) for {symbol}")
        #             await send_telegram_message(f"🚨 ALERT: Order notional too small for {symbol}! Req: {usdt_amount}, Min: {min_notional}")
        #             return False, "Order notional too small."
        
        # ทำการปัดเศษ Quantity ให้ถูกต้องตามที่ Binance กำหนด (สำคัญมาก!)
        # Binance มีกฎการปัดเศษที่แตกต่างกันไปในแต่ละคู่เหรียญ (stepSize)
        # คุณต้องดึงข้อมูล symbol info และใช้ LOT_SIZE filter เพื่อกำหนด decimal places
        # ตัวอย่างการปัดเศษแบบง่ายๆ (อาจไม่ถูกต้องสำหรับทุกคู่เหรียญ)
        # เช่น ถ้า stepSize คือ 0.001 ให้ปัดเศษ 3 ตำแหน่ง
        
        # วิธีที่ถูกต้องควรใช้ Decimal และ LOT_SIZE filter จาก get_symbol_info
        # นี่คือตัวอย่างที่ต้องระวัง:
        quantity = binance_client.quantize_quantity(quantity, symbol) # binance-python client มีฟังก์ชันช่วย
        
        if side == 'BUY':
            order = binance_client.order_market_buy(
                symbol=symbol,
                quantity=quantity
            )
        elif side == 'SELL':
            order = binance_client.order_market_sell(
                symbol=symbol,
                quantity=quantity
            )
        else:
            logging.error(f"Invalid side: {side}")
            return False, "Invalid order side."
            
        logging.info(f"Order placed: {order}")
        await send_telegram_message(f"✅ ORDER: {side} {quantity} {symbol} at {current_price} USDT")
        return True, order

    except Exception as e:
        logging.error(f"Error placing order for {symbol} ({side}) amount {usdt_amount}: {e}")
        await send_telegram_message(f"❌ ORDER FAILED: {side} {symbol} ({usdt_amount} USDT) - {e}")
        return False, str(e)


@app.route('/')
def home():
    return "Welcome to the Binance Webhook Bot! Access /webhook for functionality."

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    # ตรวจสอบ Authentication
    auth_header = request.headers.get('Authorization')
    if auth_header:
        try:
            auth_type, credentials = auth_header.split(' ', 1)
            if auth_type == 'Basic':
                import base64
                decoded_credentials = base64.b64decode(credentials).decode('utf-8')
                username, password = decoded_credentials.split(':', 1)
                if username == WEBHOOK_USERNAME and password == WEBHOOK_PASSWORD:
                    logging.info("Webhook authentication successful.")
                else:
                    logging.warning("Invalid webhook credentials.")
                    return jsonify({"status": "error", "message": "Unauthorized"}), 401
            else:
                logging.warning(f"Unsupported authentication type: {auth_type}")
                return jsonify({"status": "error", "message": "Unsupported authentication type"}), 401
        except Exception as e:
            logging.error(f"Error processing authentication header: {e}")
            return jsonify({"status": "error", "message": "Authentication error"}), 401
    else:
        logging.warning("No Authorization header provided for webhook.")
        return jsonify({"status": "error", "message": "Unauthorized: Authorization header missing"}), 401

    try:
        data = request.json
        logging.info(f"Received webhook data: {data}")

        # ตรวจสอบว่าข้อมูลที่รับมาตรงตามฟอร์แมตที่คาดหวังจาก TradingView หรือไม่
        required_keys = ['side', 'symbol', 'usdt', 'username', 'password']
        if not all(key in data for key in required_keys):
            logging.error(f"Missing required keys in webhook data. Received: {data}")
            asyncio.run(send_telegram_message(f"🚨 ALERT: Webhook data missing keys: {data}"))
            return jsonify({"status": "error", "message": "Missing required data"}), 400

        side = data.get('side').upper() # BUY/SELL
        symbol = data.get('symbol').upper() # BTCUSDT
        usdt_amount = float(data.get('usdt')) # จำนวนเงิน USDT
        # ดึง username และ password จาก webhook message (สำหรับตรวจสอบกับ Env Vars)
        received_username = data.get('username')
        received_password = data.get('password')

        # ตรวจสอบ username และ password ที่ส่งมาจาก TradingView
        if received_username != WEBHOOK_USERNAME or received_password != WEBHOOK_PASSWORD:
            logging.warning(f"Invalid username/password in webhook data. Received user: {received_username}")
            asyncio.run(send_telegram_message(f"🚨 ALERT: Invalid username/password in webhook: {received_username}"))
            return jsonify({"status": "error", "message": "Invalid username or password in message"}), 401

        # ส่งข้อความไป Telegram ทันทีเมื่อได้รับสัญญาณ
        asyncio.run(send_telegram_message(f"🔔 SIGNAL: {side} {symbol} - {usdt_amount} USDT"))

        # สั่งเทรดบน Binance
        success, result = asyncio.run(place_binance_order(symbol, side, usdt_amount))

        if success:
            return jsonify({"status": "success", "message": "Webhook processed and order attempted.", "order_result": result}), 200
        else:
            return jsonify({"status": "failed", "message": "Webhook processed but order failed.", "error": result}), 500

    except Exception as e:
        logging.error(f"Error processing webhook: {e}", exc_info=True)
        asyncio.run(send_telegram_message(f"❌ WEBHOOK ERROR: {e}"))
        return jsonify({"status": "error", "message": f"Internal server error: {e}"}), 500

if __name__ == '__main__':
    # สำหรับการรันบน Render/Production ใช้ gunicorn
    # คำสั่งนี้จะไม่ถูกรันเมื่อใช้ gunicorn
    # แต่มีประโยชน์สำหรับการทดสอบ local (ถ้าคุณไม่ใช้ gunicorn ใน local)
    app.run(host='0.0.0.0', port=os.getenv('PORT', 5000), debug=True) # ใช้ PORT จาก env var หรือ 5000