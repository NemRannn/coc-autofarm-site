import os
import requests
import time
import subprocess
from datetime import datetime
import json

# ========================================================
# CONFIGURATION
# ========================================================
BOT_TOKEN = '8539073286:AAFbnsIgs64oLxyOxv8vcIrDhrvFr1ZXpU0' 
ALLOWED_USER_ID = 6302595439

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BILLS_DIR = os.path.join(BASE_DIR, 'bills')
UPDATE_SCRIPT = os.path.join(BASE_DIR, 'update_bills.py')

# Bot States
STATE_IDLE = 'IDLE'
STATE_AWAITING_PHOTO = 'AWAITING_PHOTO'
STATE_CONFIRM_ADD = 'CONFIRM_ADD'
STATE_CONFIRM_DEL = 'CONFIRM_DEL'

# Global Session
session = {
    'state': STATE_IDLE,
    'data': None # Stores filename or index
}

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, cwd=BASE_DIR)
        print(f"Command success: {cmd}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command {cmd}: {e.stderr}")
        return False

def send_msg(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'})

def download_file(file_id, file_path):
    resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}")
    file_info = resp.json()
    if not file_info.get('ok'): return False
    file_rel_path = file_info['result']['file_path']
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_rel_path}"
    file_resp = requests.get(file_url)
    with open(file_path, 'wb') as f:
        f.write(file_resp.content)
    return True

def get_bill_list():
    # Scan directory for bill images
    files = [f for f in os.listdir(BILLS_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    files.sort()
    return files

def handle_update(update):
    global session
    if 'message' not in update: return
    msg = update['message']
    chat_id = msg['chat']['id']
    user_id = msg['from']['id']

    if user_id != ALLOWED_USER_ID:
        print(f"Unauthorized access: {user_id}")
        return

    text = msg.get('text', '')

    # --- BASIC COMMANDS ---
    if text == '/start':
        session['state'] = STATE_IDLE
        help_text = (
            "🚀 **Bill Management Bot**\n\n"
            "Các lệnh khả dụng:\n"
            "➕ /add - Để bắt đầu thêm ảnh bill mới\n"
            "📜 /list - Xem danh sách bill hiện có trên web\n"
            "❌ /del [số] - Xóa bill theo số thứ tự (VD: /del 5)\n"
            "🔄 /cancel - Hủy bỏ hành động hiện tại\n"
            "🔑 /id - Xem Chat ID của bạn"
        )
        send_msg(chat_id, help_text)
        return

    if text == '/id':
        send_msg(chat_id, f"ID của bạn: `{user_id}`")
        return

    if text == '/cancel':
        session['state'] = STATE_IDLE
        session['data'] = None
        send_msg(chat_id, "⏹️ Đã hủy hành động hiện tại.")
        return

    # --- STATE: IDLE ---
    if session['state'] == STATE_IDLE:
        if text == '/add':
            session['state'] = STATE_AWAITING_PHOTO
            send_msg(chat_id, "📸 Mời bạn gửi ảnh bill. Tôi sẽ chờ...")
        
        elif text == '/list':
            files = get_bill_list()
            if not files:
                send_msg(chat_id, "📭 Hiện chưa có bill nào.")
            else:
                list_text = "📜 **Danh sách bill:**\n"
                for i, f in enumerate(files, 1):
                    list_text += f"{i}. `{f}`\n"
                send_msg(chat_id, list_text)
        
        elif text.startswith('/del'):
            parts = text.split()
            if len(parts) < 2:
                send_msg(chat_id, "💡 Vui lòng nhập số thứ tự. VD: `/del 1`")
                return
            try:
                idx = int(parts[1]) - 1
                files = get_bill_list()
                if 0 <= idx < len(files):
                    session['state'] = STATE_CONFIRM_DEL
                    session['data'] = files[idx]
                    send_msg(chat_id, f"⚠️ **Xác nhận xóa bill này?**\nTên file: `{files[idx]}`\n\nGõ /confirm để thực hiện.")
                else:
                    send_msg(chat_id, "❌ Số thứ tự không tồn tại trong danh sách.")
            except ValueError:
                send_msg(chat_id, "❌ Vui lòng nhập số hợp lệ.")

    # --- STATE: AWAITING_PHOTO ---
    elif session['state'] == STATE_AWAITING_PHOTO:
        if 'photo' in msg:
            photo = msg['photo'][-1]
            file_id = photo['file_id']
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bill_{timestamp}.jpg"
            file_path = os.path.join(BILLS_DIR, filename)
            
            if download_file(file_id, file_path):
                session['state'] = STATE_CONFIRM_ADD
                session['data'] = filename
                send_msg(chat_id, f"📥 Đã tải ảnh xong.\nTên file: `{filename}`\n\n✅ Gõ /confirm để cập nhật lên web.")
            else:
                send_msg(chat_id, "❌ Lỗi khi tải ảnh. Thử lại hoặc /cancel.")
        else:
            send_msg(chat_id, "⚠️ Vui lòng gửi một tấm ảnh hoặc gõ /cancel.")

    # --- STATE: CONFIRMS ---
    elif text == '/confirm':
        if session['state'] == STATE_CONFIRM_ADD:
            filename = session['data']
            send_msg(chat_id, "🔄 Đang cập nhật web và Git...")
            
            run_command(f"python \"{UPDATE_SCRIPT}\"")
            run_command("git add .")
            run_command(f"git commit -m \"Add bill via Bot: {filename}\"")
            run_command("git push")
            
            send_msg(chat_id, f"🎉 **Thành công!** Bill `{filename}` đã lên web.")
            session['state'] = STATE_IDLE
            session['data'] = None

        elif session['state'] == STATE_CONFIRM_DEL:
            filename = session['data']
            file_path = os.path.join(BILLS_DIR, filename)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                send_msg(chat_id, f"🗑️ Đã xóa file `{filename}`. Đang cập nhật web...")
                
                run_command(f"python \"{UPDATE_SCRIPT}\"")
                run_command("git add .")
                run_command(f"git commit -m \"Delete bill via Bot: {filename}\"")
                run_command("git push")
                
                send_msg(chat_id, "✅ Đã cập nhật xong.")
            else:
                send_msg(chat_id, "❌ Lỗi: File không tìm thấy trên ổ đĩa.")
            
            session['state'] = STATE_IDLE
            session['data'] = None
        else:
            send_msg(chat_id, "🤔 Bạn không có hành động nào chờ xác nhận.")

def main():
    print("Bot starting (Pro Version)...")
    last_update_id = 0
    # Clean up old updates to avoid duplication
    resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-1")
    data = resp.json()
    if data.get('ok') and data['result']:
        last_update_id = data['result'][0]['update_id']

    while True:
        try:
            resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=30")
            data = resp.json()
            if data.get('ok'):
                for update in data['result']:
                    handle_update(update)
                    last_update_id = update['update_id']
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
