from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("✅ ได้รับ Webhook:", data)

    # ตัวอย่าง: ถ้า data['action'] == "buy":
    if data.get("action") == "buy":
        # เรียก Binance API ตรงนี้ (สามารถใส่โค้ดได้)
        print("สั่งซื้อแล้วครับ")

    return jsonify({"status": "received"}), 200

if __name__ == '__main__':
    app.run()
