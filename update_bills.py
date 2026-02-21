import os
import re
import json

# Configuration
HTML_FILE = 'index.html'
BILLS_DIR = 'bills'
BACKUP_FILE = 'index.html.bak'

def update_bills():
    print(f"--- Updating bills from '{BILLS_DIR}/' to '{HTML_FILE}' ---")

    # 1. Get current images in folder
    if not os.path.exists(BILLS_DIR):
        print(f"Error: Directory '{BILLS_DIR}' not found.")
        return

    valid_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
    folder_images = [f for f in os.listdir(BILLS_DIR) if f.lower().endswith(valid_extensions)]
    folder_images.sort()
    
    print(f"Found {len(folder_images)} images in '{BILLS_DIR}/'.")

    # 2. Read index.html
    if not os.path.exists(HTML_FILE):
        print(f"Error: '{HTML_FILE}' not found.")
        return

    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # 3. Extract current BILL_IMAGES array using regex
    # Matches: const BILL_IMAGES = [ ... ];
    pattern = r'(const BILL_IMAGES = )(\[[\s\S]*?\])(;)'
    match = re.search(pattern, content)
    
    if not match:
        print("Error: Could not find 'const BILL_IMAGES' array in index.html.")
        return

    prefix = match.group(1)
    current_json_str = match.group(2)
    suffix = match.group(3)

    # Clean up JSON-like JS array to valid JSON
    # 1. Replace single quotes with double quotes (basic attempt)
    # 2. Handle trailing commas
    json_ready = current_json_str.replace("'", '"')
    json_ready = re.sub(r',\s*\]', ']', json_ready)
    
    try:
        current_data = json.loads(json_ready)
    except Exception as e:
        print(f"Warning: Could not parse existing array perfectly ({e}). Starting fresh.")
        current_data = []

    # Map current data by filename for lookup
    data_map = {item['file'].split('/')[-1]: item for item in current_data}

    # 4. Build new list
    new_data = []
    for idx, img_name in enumerate(folder_images, 1):
        # Always use a generic "Customer" author as index.html now handles bilingual display
        item = {
            "file": f"bills/{img_name}",
            "author": "Customer"
        }
        
        new_data.append(item)

    # 5. Generate new JS array string
    # We use json.dumps then convert back to "JS style" with single quotes for consistency
    new_json_str = json.dumps(new_data, indent=6, ensure_ascii=False)
    # Convert double quotes to single quotes for the "looks" in JS
    # (Note: This is just for aesthetics, valid JS array)
    new_js_array = new_json_str.replace('"', "'")

    # 6. Replace and save
    new_content = content[:match.start()] + prefix + new_js_array + suffix + content[match.end():]

    # Create backup
    import shutil
    shutil.copy2(HTML_FILE, BACKUP_FILE)
    
    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"Success! Updated {len(new_data)} items. Backup saved as '{BACKUP_FILE}'.")
    print("Refresh your browser to see the changes.")

if __name__ == "__main__":
    update_bills()
