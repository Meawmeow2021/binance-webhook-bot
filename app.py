from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to the Binance Webhook Bot! Access /webhook for functionality." # แก้ไขข้อความแจ้งเตือนด้วย

# >>> แก้ไขตรงนี้ <<<
@app.route('/webhook', methods=['POST']) # เปลี่ยนจาก '/hook' เป็น '/webhook'
def handle_webhook():
    if request.method == 'POST':
        data = request.json
        print(f"Received webhook data: {data}")
        # ทำสิ่งที่คุณต้องการกับข้อมูล
        return jsonify({"status": "success", "message": "Webhook received"}), 200
    else:
        return jsonify({"status": "error", "message": "Only POST requests are allowed on this endpoint"}), 405

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=False)