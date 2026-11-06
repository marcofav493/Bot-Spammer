import json
import os
import time
import random
import string
import asyncio
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)

# =========================================================
# CONFIG
# =========================================================
BOT_TOKEN = "9146464981:AAG2NRgWDMcXhgx5fPcBkmD-xvARMTYKtzA"
ADMIN_ID = 7372943244  # Ganti pake ID Telegram lu
DB_FILE = "keys.json"

# State buat ConversationHandler
(
    GATE_KEY, 
    MAIN_MENU,
    SPAM_URL,
    SPAM_PICK_MSG, SPAM_CUSTOM_MSG, 
    SPAM_PICK_COUNT, SPAM_CUSTOM_COUNT,
    SPAM_PICK_DELAY, SPAM_CUSTOM_DELAY,
    SPAM_CONFIRM, SPAM_IMG,
    TEST_URL,
    DEL_URL,
    ADMIN_PREFIX, ADMIN_DAY, ADMIN_HOUR, ADMIN_MIN, ADMIN_QUOTA, ADMIN_AMOUNT
) = range(19)

# =========================================================
# DATABASE (JSON)
# =========================================================
def load_db():
    if not os.path.exists(DB_FILE):
        return {"keys": []}
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"keys": []}

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def gen_key(prefix="MXZ"):
    chars = string.ascii_uppercase + string.digits
    seg = lambda: ''.join(random.choices(chars, k=4))
    return f"{prefix.upper()}-{seg()}-{seg()}-{seg()}"

def fmt_time(ts):
    if not ts: return "-"
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")

def get_key_data(key_str):
    db = load_db()
    for k in db["keys"]:
        if k["key"] == key_str:
            return k
    return None

def save_key_data(k):
    db = load_db()
    for i, x in enumerate(db["keys"]):
        if x["key"] == k["key"]:
            db["keys"][i] = k
            save_db(db)
            return
    db["keys"].append(k)
    save_db(db)

# =========================================================
# GATE KEY & LOGIN
# =========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🔐 *MARCOXZ SECURE ENTRY*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Masukin key lu buat akses bot.\n"
        "Belum punya key? Minta ke admin.\n\n"
        "Ketik /cancel buat batal."
    )
    await update.message.reply_text(msg, parse_mode='Markdown')
    return GATE_KEY

async def process_gate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key_input = update.message.text.strip()
    k = get_key_data(key_input)
    
    if not k:
        await update.message.reply_text("❌ *KEY TIDAK DITEMUKAN.*\nCoba lagi atau minta admin.", parse_mode='Markdown')
        return GATE_KEY
        
    if time.time() > k["expiresAt"]:
        await update.message.reply_text("❌ *KEY EXPIRED.*\nMinta key baru ke admin.", parse_mode='Markdown')
        return GATE_KEY
        
    if k["used"] >= k["quota"]:
        await update.message.reply_text("❌ *KUOTA HABIS.*\nMinta key baru ke admin.", parse_mode='Markdown')
        return GATE_KEY

    # Simpan session
    context.user_data['session_key'] = k["key"]
    
    await update.message.reply_text(
        f"✅ *ACCESS GRANTED*\n"
        f"Key: `{k['key']}`\n"
        f"Sisa Kuota: `{k['quota'] - k['used']} / {k['quota']}`\n"
        f"Expired: `{fmt_time(k['expiresAt'])}`\n\n"
        f"Ketik /menu buat mulai.",
        parse_mode='Markdown'
    )
    return MAIN_MENU

# =========================================================
# MAIN MENU
# =========================================================
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('session_key'):
        await update.message.reply_text("🔐 Lu belum login. Ketik /start dulu.")
        return GATE_KEY
        
    kb = [
        [InlineKeyboardButton("📨 Webhook Spammer", callback_data="menu_spammer")],
        [InlineKeyboardButton("🔍 Cek Webhook (On/Off)", callback_data="menu_tester")],
        [InlineKeyboardButton("🗑 Hapus Webhook", callback_data="menu_deleter")],
        [InlineKeyboardButton("📊 Cek Kuota", callback_data="menu_quota")],
        [InlineKeyboardButton("🚪 Logout", callback_data="menu_logout")]
    ]
    reply_markup = InlineKeyboardMarkup(kb)
    
    await update.message.reply_text(
        "⚡ *PMSW - MarcoXz*\n"
        "// PERSATUAN MUWANI SPAMMER WEBHOOK\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Pilih menu di bawah:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return MAIN_MENU

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    key_str = context.user_data.get('session_key')
    if not key_str:
        await query.edit_message_text("🔐 Session habis. Ketik /start.")
        return GATE_KEY

    if data == "menu_spammer":
        await query.edit_message_text(
            "📨 *WEBHOOK SPAMMER*\n\n"
            "Masukin URL Webhook Discord dulu ya (bisa copas dari web):", 
            parse_mode='Markdown'
        )
        return SPAM_URL
        
    elif data == "menu_tester":
        await query.edit_message_text("🔍 *CEK WEBHOOK (ON/OFF)*\n\nMasukin URL Webhook Discord yang mau dicek:", parse_mode='Markdown')
        return TEST_URL
        
    elif data == "menu_deleter":
        await query.edit_message_text("🗑 *HAPUS WEBHOOK*\n\nMasukin URL Webhook Discord yang mau dihapus permanen:\n_(Hati-hati, ini nggak bisa dibalikin!)_", parse_mode='Markdown')
        return DEL_URL
        
    elif data == "menu_quota":
        k = get_key_data(key_str)
        await query.edit_message_text(
            f"📊 *INFO KEY*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Key: `{k['key']}`\n"
            f"Kuota: `{k['quota'] - k['used']} / {k['quota']}`\n"
            f"Expired: `{fmt_time(k['expiresAt'])}`",
            parse_mode='Markdown'
        )
        return MAIN_MENU
        
    elif data == "menu_logout":
        context.user_data.clear()
        await query.edit_message_text("🚪 Lu udah logout. Ketik /start buat masuk lagi.")
        return GATE_KEY

# =========================================================
# SPAM FLOW (FULL BUTTONS)
# =========================================================
async def spam_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("https://discord.com/api/webhooks/"):
        await update.message.reply_text("❌ URL Webhook nggak valid. Harus mulai dari `https://discord.com/api/webhooks/...`", parse_mode='Markdown')
        return SPAM_URL
        
    context.user_data['spam_url'] = url
    
    # Pilihan Pesan
    kb = [
        [InlineKeyboardButton("@everyone Spam!", callback_data="msg_everyone")],
        [InlineKeyboardButton("Woy Kontol!", callback_data="msg_woy")],
        [InlineKeyboardButton("Server Jebol!", callback_data="msg_jebol")],
        [InlineKeyboardButton("✍️ Ketik Sendiri (Custom)", callback_data="msg_custom")]
    ]
    await update.message.reply_text(
        "✅ URL disimpan.\n\n"
        "Sekarang pilih *pesan* yang mau dikirim:", 
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode='Markdown'
    )
    return SPAM_PICK_MSG

async def spam_msg_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "msg_custom":
        await query.edit_message_text("✍️ *CUSTOM PESAN*\n\nKetik pesan yang mau lu kirim sekarang:")
        return SPAM_CUSTOM_MSG
        
    # Mapping tombol ke teks
    msg_map = {
        "msg_everyone": "@everyone SERVER KENA SPAM!",
        "msg_woy": "@everyone WOY KONTOL!",
        "msg_jebol": "SERVER INI UDAH JEBOLL!!"
    }
    context.user_data['spam_msg'] = msg_map.get(data, "Spam!")
    
    return await pilih_jumlah_spam(query, context)

async def spam_custom_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
    if not msg:
        await update.message.reply_text("❌ Pesan nggak boleh kosong.")
        return SPAM_CUSTOM_MSG
        
    context.user_data['spam_msg'] = msg
    return await pilih_jumlah_spam(update, context)

async def pilih_jumlah_spam(msg_obj, context: ContextTypes.DEFAULT_TYPE):
    # Ambil sisa kuota buat info
    key_str = context.user_data.get('session_key')
    k = get_key_data(key_str)
    sisa = k["quota"] - k["used"] if k else 0
    
    kb = [
        [InlineKeyboardButton(f"10x", callback_data="cnt_10"), InlineKeyboardButton(f"50x", callback_data="cnt_50")],
        [InlineKeyboardButton(f"100x", callback_data="cnt_100"), InlineKeyboardButton(f"Maksimal ({sisa}x)", callback_data="cnt_max")],
        [InlineKeyboardButton("✍️ Ketik Sendiri (Custom)", callback_data="cnt_custom")]
    ]
    
    text = (
        "✅ Pesan disimpan.\n\n"
        "Sekarang pilih *jumlah spam*:\n"
        f"_(Sisa kuota lu saat ini: `{sisa}`)_"
    )
    
    if hasattr(msg_obj, 'edit_message_text'):
        await msg_obj.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else:
        await msg_obj.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        
    return SPAM_PICK_COUNT

async def spam_count_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "cnt_custom":
        await query.edit_message_text("✍️ *CUSTOM JUMLAH*\n\nKetik angka jumlah spam yang mau lu kirim:")
        return SPAM_CUSTOM_COUNT
        
    key_str = context.user_data.get('session_key')
    k = get_key_data(key_str)
    sisa = k["quota"] - k["used"]
    
    if data == "cnt_max":
        count = sisa
    else:
        count = int(data.split('_')[1])
        
    # AUTO CLAMP
    if count > sisa:
        count = sisa
        await query.answer(f"⚠️ Dipotong ke {sisa} (sesuai sisa kuota)", show_alert=True)
    
    if count <= 0:
        await query.edit_message_text("❌ Kuota lu habis bre. Nggak bisa spam.")
        return MAIN_MENU
        
    context.user_data['spam_count'] = count
    return await pilih_delay(query, context)

async def spam_custom_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Harus angka bre.")
        return SPAM_CUSTOM_COUNT

    key_str = context.user_data.get('session_key')
    k = get_key_data(key_str)
    sisa = k["quota"] - k["used"]

    if sisa <= 0:
        await update.message.reply_text("❌ Kuota lu habis bre. Nggak bisa spam.")
        return MAIN_MENU

    # AUTO CLAMP
    if count > sisa:
        count = sisa
        await update.message.reply_text(f"⚠️ *AUTO-CLAMP:* Lu ngetik lebih dari kuota. Sistem potong jadi `{count}`.", parse_mode='Markdown')
    elif count < 1:
        count = 1

    context.user_data['spam_count'] = count
    return await pilih_delay(update, context)

async def pilih_delay(msg_obj, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("Cepat (100ms)", callback_data="dly_100")],
        [InlineKeyboardButton("Normal (500ms)", callback_data="dly_500")],
        [InlineKeyboardButton("Aman (1000ms)", callback_data="dly_1000")],
        [InlineKeyboardButton("✍️ Ketik Sendiri (Custom)", callback_data="dly_custom")]
    ]
    
    text = "✅ Jumlah disimpan.\n\nTerakhir, pilih *delay antar kirim* (ms):"
    
    if hasattr(msg_obj, 'edit_message_text'):
        await msg_obj.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await msg_obj.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
        
    return SPAM_PICK_DELAY

async def spam_delay_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "dly_custom":
        await query.edit_message_text("✍️ *CUSTOM DELAY*\n\nKetik delay (contoh: `500`):")
        return SPAM_CUSTOM_DELAY
        
    delay = int(data.split('_')[1])
    context.user_data['spam_delay'] = delay
    return await konfirmasi_spam(query, context)

async def spam_custom_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        delay = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Harus angka bre.")
        return SPAM_CUSTOM_DELAY

    if delay < 50: delay = 50
    if delay > 5000: delay = 5000
    context.user_data['spam_delay'] = delay
    return await konfirmasi_spam(update, context)

async def konfirmasi_spam(msg_obj, context: ContextTypes.DEFAULT_TYPE):
    url = context.user_data.get('spam_url')
    msg = context.user_data.get('spam_msg')
    count = context.user_data.get('spam_count', 1)
    delay = context.user_data.get('spam_delay', 500)
    
    kb = [
        [InlineKeyboardButton("🚀 MULAI SPAM SEKARANG", callback_data="do_spam")],
        [InlineKeyboardButton("🖼 Tambah Gambar (Opsional)", callback_data="add_img")],
        [InlineKeyboardButton("❌ Batal", callback_data="batal_spam")]
    ]
    
    text = (
        "📝 *KONFIRMASI SPAM*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 *URL:* `{url[-20:]}`...\n" # Cuma nampilin ujungnya biar rapi
        f"💬 *Pesan:* `{msg}`\n"
        f"🔢 *Jumlah:* `{count}x`\n"
        f"⏱️ *Delay:* `{delay}ms`\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Siap diluncurkan?"
    )
    
    if hasattr(msg_obj, 'edit_message_text'):
        await msg_obj.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else:
        await msg_obj.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        
    return SPAM_CONFIRM

async def spam_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "batal_spam":
        context.user_data.pop('spam_url', None)
        context.user_data.pop('spam_msg', None)
        context.user_data.pop('spam_count', None)
        context.user_data.pop('spam_delay', None)
        await query.edit_message_text("❌ Spam dibatalkan. Ketik /menu buat balik.")
        return MAIN_MENU
        
    elif data == "add_img":
        await query.edit_message_text(
            "🖼 *UPLOAD GAMBAR*\n\n"
            "Silakan kirim fotonya sekarang, atau ketik /skip buat lanjut tanpa gambar.",
            parse_mode='Markdown'
        )
        return SPAM_IMG
        
    elif data == "do_spam":
        # Panggil fungsi eksekusi, pake dummy update biar function-nya jalan
        return await eksekusi_spam_update(query, context)

async def spam_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        context.user_data['spam_img_url'] = photo_file.file_path
    else:
        context.user_data['spam_img_url'] = None
        
    # Langsung eksekusi setelah gambar diupload
    return await eksekusi_spam_update(update, context)

async def spam_skip_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['spam_img_url'] = None
    return await eksekusi_spam_update(update, context)

async def eksekusi_spam_update(msg_obj, context: ContextTypes.DEFAULT_TYPE):
    url = context.user_data.get('spam_url')
    msg = context.user_data.get('spam_msg')
    count = context.user_data.get('spam_count', 1)
    delay = context.user_data.get('spam_delay', 500)
    img_url = context.user_data.get('spam_img_url')
    key_str = context.user_data.get('session_key')

    context.user_data['stop_spam'] = False

    # Handle edit vs reply
    if hasattr(msg_obj, 'edit_message_text'):
        await msg_obj.edit_message_text(f"🚀 *SPAM DIMULAI...* ({count}x)\n\n_Ketik /stop untuk membatalkan._", parse_mode='Markdown')
    else:
        await msg_obj.message.reply_text(f"🚀 *SPAM DIMULAI...* ({count}x)\n\n_Ketik /stop untuk membatalkan._", parse_mode='Markdown')

    sent = 0
    for i in range(count):
        if context.user_data.get('stop_spam'):
            if hasattr(msg_obj, 'message'):
                await msg_obj.message.reply_text("⏹ *SPAM DIHENTIKAN OLEH USER.*", parse_mode='Markdown')
            break

        k = get_key_data(key_str)
        if not k or time.time() > k["expiresAt"]:
            break
        if k["used"] >= k["quota"]:
            break

        k["used"] += 1
        save_key_data(k)

        payload = {"content": msg}
        if img_url:
            payload["embeds"] = [{"image": {"url": img_url}}]

        try:
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code == 204:
                sent += 1
            elif res.status_code == 429:
                await asyncio.sleep(5)
        except:
            pass

        await asyncio.sleep(delay / 1000)

    k = get_key_data(key_str)
    sisa = k["quota"] - k["used"] if k else 0
    
    end_text = (
        f"✅ *PROSES SELESAI!*\n"
        f"Total Terkirim: `{sent}`\n"
        f"Sisa Kuota: `{sisa} / {k['quota']}`\n\n"
        f"Ketik /menu buat balik."
    )
    
    if hasattr(msg_obj, 'message'):
        await msg_obj.message.reply_text(end_text, parse_mode='Markdown')
    else:
        await msg_obj.reply_text(end_text, parse_mode='Markdown')
        
    return MAIN_MENU

async def stop_spam_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('stop_spam') is False:
        context.user_data['stop_spam'] = True
        await update.message.reply_text("⏹ *Sinyal berhenti diterima...*", parse_mode='Markdown')
    else:
        await update.message.reply_text("⚠️ Nggak ada proses spam yang lagi jalan.")

# =========================================================
# WEBHOOK TESTER & DELETER
# =========================================================
async def test_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("https://discord.com/api/webhooks/"):
        await update.message.reply_text("❌ URL Webhook nggak valid.")
        return TEST_URL

    await update.message.reply_text("⏳ *Mengecek webhook...*", parse_mode='Markdown')
    try:
        res = requests.post(url, json={"content": "✅ Webhook aktif!"}, timeout=10)
        if res.status_code == 204:
            await update.message.reply_text("🟢 *WEBHOOK AKTIF (ON)*", parse_mode='Markdown')
        elif res.status_code in [401, 404]:
            await update.message.reply_text(f"🔴 *WEBHOOK MATI (OFF)*\nHTTP {res.status_code}", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"⚠️ HTTP Status: `{res.status_code}`", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: `{str(e)}`", parse_mode='Markdown')

    await menu(update, context)
    return MAIN_MENU

async def del_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("https://discord.com/api/webhooks/"):
        await update.message.reply_text("❌ URL Webhook nggak valid.")
        return DEL_URL

    await update.message.reply_text("⏳ *Menghapus webhook...*", parse_mode='Markdown')
    try:
        res = requests.delete(url, timeout=10)
        if res.status_code == 204:
            await update.message.reply_text("✅ *WEBHOOK BERHASIL DIHAPUS PERMANEN!*", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ Gagal. HTTP `{res.status_code}`", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: `{str(e)}`", parse_mode='Markdown')

    await menu(update, context)
    return MAIN_MENU

# =========================================================
# ADMIN PANEL
# =========================================================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Lu bukan admin.")
        return MAIN_MENU

    kb = [
        [InlineKeyboardButton("🔑 Generate Key", callback_data="admin_gen")],
        [InlineKeyboardButton("📋 List Keys", callback_data="admin_list")],
        [InlineKeyboardButton("🗑 Hapus Semua Keys", callback_data="admin_wipe")]
    ]
    await update.message.reply_text(
        "⚙ *ADMIN PANEL — ROOT*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Pilih aksi:",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode='Markdown'
    )
    return MAIN_MENU

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text("❌ Lu bukan admin.")
        return MAIN_MENU

    data = query.data
    if data == "admin_gen":
        await query.edit_message_text("🔑 *GENERATE KEY*\n\nMasukin *Prefix* (contoh: `ZAXZZ`):", parse_mode='Markdown')
        return ADMIN_PREFIX
    elif data == "admin_list":
        db = load_db()
        if not db["keys"]:
            await query.edit_message_text("📋 Belum ada key.")
            return MAIN_MENU
        text = "📋 *LIST KEYS*\n━━━━━━━━━━━━━━━━━━━━━\n"
        for k in db["keys"]:
            sisa = k["quota"] - k["used"]
            status = "EXPIRED" if time.time() > k["expiresAt"] else ("HABIS" if sisa <=0 else "AKTIF")
            text += f"`{k['key']}` | {sisa}/{k['quota']} | {status}\n"
        await query.edit_message_text(text, parse_mode='Markdown')
        return MAIN_MENU
    elif data == "admin_wipe":
        db = load_db()
        db["keys"] = []
        save_db(db)
        await query.edit_message_text("✅ Semua key berhasil dihapus.")
        return MAIN_MENU

async def admin_prefix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prefix = update.message.text.strip().upper().replace(" ", "")
    context.user_data['adm_prefix'] = prefix or "MXZ"
    await update.message.reply_text("✅ Prefix disimpan.\n\nMasukin *Durasi HARI*:")
    return ADMIN_DAY

async def admin_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: day = int(update.message.text.strip())
    except: return await update.message.reply_text("❌ Harus angka.")
    context.user_data['adm_day'] = day
    await update.message.reply_text("Masukin *Durasi JAM*:")
    return ADMIN_HOUR

async def admin_hour(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: hour = int(update.message.text.strip())
    except: return await update.message.reply_text("❌ Harus angka.")
    context.user_data['adm_hour'] = hour
    await update.message.reply_text("Masukin *Durasi MENIT*:")
    return ADMIN_MIN

async def admin_min(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: minute = int(update.message.text.strip())
    except: return await update.message.reply_text("❌ Harus angka.")
    context.user_data['adm_min'] = minute
    await update.message.reply_text("Masukin *KUOTA SPAM*:")
    return ADMIN_QUOTA

async def admin_quota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: quota = int(update.message.text.strip())
    except: return await update.message.reply_text("❌ Harus angka.")
    context.user_data['adm_quota'] = quota
    await update.message.reply_text("Masukin *JUMLAH KEY* yang mau dibikin:")
    return ADMIN_AMOUNT

async def admin_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: amount = int(update.message.text.strip())
    except: return await update.message.reply_text("❌ Harus angka.")
    
    prefix = context.user_data.get('adm_prefix', 'MXZ')
    day = context.user_data.get('adm_day', 0)
    hour = context.user_data.get('adm_hour', 0)
    minute = context.user_data.get('adm_min', 0)
    quota = context.user_data.get('adm_quota', 1)
    
    dur_ms = ((day * 24 + hour) * 60 + minute) * 60
    now_ts = time.time()
    expires = now_ts + dur_ms
    
    db = load_db()
    made = []
    for _ in range(amount):
        new_key = gen_key(prefix)
        obj = {"key": new_key, "createdAt": now_ts, "expiresAt": expires, "quota": quota, "used": 0}
        db["keys"].append(obj)
        made.append(obj)
    save_db(db)
    
    text = f"✅ *{amount} KEY DIBUAT!*\nPrefix: `{prefix}`\nDurasi: `{day}h {hour}j {minute}m`\nKuota: `{quota}`\n━━━━━━━━━━━━━━━━━━━━━\n"
    for k in made:
        text += f"`{k['key']}`\n"
        
    await update.message.reply_text(text, parse_mode='Markdown')
    await menu(update, context)
    return MAIN_MENU

# =========================================================
# CANCEL & ERROR HANDLING
# =========================================================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚪 Dibatalkan. Ketik /menu buat balik.")
    return MAIN_MENU

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"Error: {context.error}")

# =========================================================
# MAIN
# =========================================================
def main():
    app = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("menu", menu),
            CommandHandler("admin", admin_panel)
        ],
        states={
            GATE_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_gate)],
            MAIN_MENU: [CallbackQueryHandler(menu_callback, pattern="^menu_"), CallbackQueryHandler(admin_callback, pattern="^admin_")],
            
            # SPAM FLOW (BUTTONS)
            SPAM_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, spam_url)],
            SPAM_PICK_MSG: [CallbackQueryHandler(spam_msg_callback, pattern="^msg_")],
            SPAM_CUSTOM_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, spam_custom_msg)],
            SPAM_PICK_COUNT: [CallbackQueryHandler(spam_count_callback, pattern="^cnt_")],
            SPAM_CUSTOM_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, spam_custom_count)],
            SPAM_PICK_DELAY: [CallbackQueryHandler(spam_delay_callback, pattern="^dly_")],
            SPAM_CUSTOM_DELAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, spam_custom_delay)],
            SPAM_CONFIRM: [CallbackQueryHandler(spam_confirm_callback, pattern="^(do_spam|add_img|batal_spam)$")],
            SPAM_IMG: [
                MessageHandler(filters.PHOTO, spam_image),
                CommandHandler("skip", spam_skip_image)
            ],
            
            # LAINNYA
            TEST_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, test_url)],
            DEL_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, del_url)],
            ADMIN_PREFIX: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_prefix)],
            ADMIN_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_day)],
            ADMIN_HOUR: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_hour)],
            ADMIN_MIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_min)],
            ADMIN_QUOTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_quota)],
            ADMIN_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_amount)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    app.add_handler(CommandHandler("stop", stop_spam_cmd))
    app.add_handler(conv_handler)
    app.add_error_handler(error_handler)

    print("Bot jalan...")
    app.run_polling()

if __name__ == '__main__':
    main()