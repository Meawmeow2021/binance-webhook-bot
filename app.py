from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to the Binance Webhook Bot! Access /hook for functionality."

@app.route('/hook', methods=['POST']) # หรือ methods=['GET', 'POST'] ถ้าต้องการรับ GET ด้วย
def handle_webhook():
    if request.method == 'POST':
        # ตรวจสอบและประมวลผลข้อมูลที่ส่งมาจาก webhook
        # ตัวอย่างเช่น:
        data = request.json # หรือ request.form ถ้าเป็น form data
        print(f"Received webhook data: {data}")
        # ทำสิ่งที่คุณต้องการกับข้อมูล เช่น ส่งไป Telegram, Line, ฯลฯ
        return jsonify({"status": "success", "message": "Webhook received"}), 200
    else:
        return jsonify({"status": "error", "message": "Only POST requests are allowed on this endpoint"}), 405

if __name__ == '__main__':
    # Development server - ไม่ควรใช้ใน production
    app.run(host='0.0.0.0', port=10000, debug=False)