import os
import requests
import time
import subprocess
from datetime import datetime

# ========================================================
# CẤU HÌNH (CONFIGURATION)
# 1. Liên hệ @BotFather trên Telegram để lấy TOKEN.
# 2. Gửi bất kỳ ảnh nào cho Bot rồi xem ID người gửi trong Terminal.
# 3. Điền ID đó vào ALLOWED_USER_ID để chỉ bạn mới dùng được Bot.
# ========================================================
BOT_TOKEN = '8539073286:AAFbnsIgs64oLxyOxv8vcIrDhrvFr1ZXpU0' 
ALLOWED_USER_ID = 6302595439  # Điền Chat ID của bạn vào đây (Số nguyên)

# Cấu hình đường dẫn
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BILLS_DIR = os.path.join(BASE_DIR, 'bills')
UPDATE_SCRIPT = os.path.join(BASE_DIR, 'update_bills.py')

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, cwd=BASE_DIR)
        print(f"Command success: {cmd}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command {cmd}: {e.stderr}")
        return None

def download_file(file_id, file_path):
    # Lấy đường dẫn file từ Telegram
    resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}")
    file_info = resp.json()
    if not file_info.get('ok'):
        return False
    
    file_rel_path = file_info['result']['file_path']
    # Tải file về
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_rel_path}"
    file_resp = requests.get(file_url)
    
    with open(file_path, 'wb') as f:
        f.write(file_resp.content)
    return True

UPLOAD_HISTORY = []

def handle_update(update):
    global UPLOAD_HISTORY
    if 'message' not in update: return
    msg = update['message']
    user_id = msg['from']['id']
    username = msg['from'].get('username', 'Unknown')

    # Bảo mật: Chỉ cho phép User được định danh
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        print(f"Blocked message from {user_id} ({username})")
        return

    # Lệnh văn bản
    if 'text' in msg:
        text = msg['text']
        if text == '/start':
            welcome_text = (
                "👋 Chào mừng bạn đến với Bill Up Bot!\n\n"
                "Tôi giúp bạn cập nhật bill thanh toán lên web nhanh chóng.\n"
                "📸 **Cách dùng:** Bạn chỉ cần gửi ảnh bill trực tiếp cho tôi.\n"
                "🗑️ **Xóa nhầm:** Gõ /del để xóa ảnh vừa gửi.\n"
                "🔑 **ID của bạn:** Gõ /id để lấy Chat ID cài đặt bảo mật."
            )
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={user_id}&text={welcome_text}")
            return

        if text == '/id':
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={user_id}&text=ID của bạn là: {user_id}")
            return
        
        if text == '/del':
            if not UPLOAD_HISTORY:
                # Tìm file mới nhất trong thư mục nếu history trống
                files = [f for f in os.listdir(BILLS_DIR) if f.startswith('bill_')]
                if files:
                    files.sort()
                    last_file = files[-1]
                else:
                    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={user_id}&text=❌ Không có bill nào để xóa.")
                    return
            else:
                last_file = UPLOAD_HISTORY.pop()

            file_path = os.path.join(BILLS_DIR, last_file)
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted: {last_file}")
                
                # Cập nhật web
                run_command(f"python \"{UPDATE_SCRIPT}\"")
                run_command("git add .")
                run_command(f"git commit -m \"Auto-delete bill from Telegram: {last_file}\"")
                run_command("git push")
                
                requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={user_id}&text=✅ Đã xóa bill mới nhất và cập nhật web!")
            else:
                requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={user_id}&text=❌ File không tồn tại để xóa.")
            return

    # Nếu gửi ảnh
    if 'photo' in msg:
        # Lấy ảnh chất lượng tốt nhất
        photo = msg['photo'][-1]
        file_id = photo['file_id']
        
        # Tạo tên file theo thời gian
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bill_{timestamp}.jpg"
        file_path = os.path.join(BILLS_DIR, filename)
        
        # 1. Tải ảnh
        if download_file(file_id, file_path):
            print(f"Saved: {filename}")
            UPLOAD_HISTORY.append(filename)
            
            # 2. Run HTML update script
            run_command(f"python \"{UPDATE_SCRIPT}\"")
            
            # 3. Git Push (Auto deploy)
            print("Pushing to Git...")
            run_command("git add .")
            run_command(f"git commit -m \"Auto-add bill from Telegram: {filename}\"")
            run_command("git push")
            
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={user_id}&text=✅ Đã thêm bill và cập nhật web thành công! Gõ /del để xóa nếu nhầm.")
        else:
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={user_id}&text=❌ Lỗi khi tải ảnh.")

def main():
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("Vui lòng điền BOT_TOKEN vào file tele_bill_bot.py!")
        return

    print("Bot is running... Send photos to the Bot on Telegram.")
    print("Tip: Send /id to the Bot to get your ID for ALLOWED_USER_ID.")
    
    last_update_id = 0
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
