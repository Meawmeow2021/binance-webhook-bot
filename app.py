from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route('/')
def index():
    return 'Hello! Bot is working.'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    # ตรวจสอบ user/pwd (สามารถเพิ่ม logic ได้)
    print("Received data:", data)
    return jsonify({'status': 'success', 'message': 'Webhook received!'})

if __name__ == '__main__':
    app.run(debug=True)
