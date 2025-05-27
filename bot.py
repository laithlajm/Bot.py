import telebot
from telebot import types
import requests
from datetime import datetime, timedelta
import json
import os
import re
import time

BOT_TOKEN = "7832899750:AAGmRu3Yew5HK1Wa1En6ByxFWZSiSpv4wR0"
ADMIN_ID = 6393580417
DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({
                "balance": {str(ADMIN_ID): 50},
                "banned": [],
                "api_key": "4bd8790b585b6d66081849b6670eb5ce601826aab1b1c8b7b814c5bfbd531c8e",
                "users": [],
                "proxies": {},
                "prices": {"3hours": 0.5, "12hours": 1.5, "day": 3, "week": 15, "month": 40},
                "payment_methods": {
                    "payeer": {"address": "P1234567890", "active": True, "reason": "", "min_amount": 5, "max_amount": 1000, "exchange_rate": 1, "name": "Payeer"},
                    "ltc": {"address": "ltc1qxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxc8", "active": True, "reason": "", "min_amount": 10, "max_amount": 5000, "exchange_rate": 1, "name": "LTC"},
                    "trx": {"address": "TXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", "active": True, "reason": "", "min_amount": 5, "max_amount": 2000, "exchange_rate": 1, "name": "TRX"},
                    "usdt_bep20": {"address": "USDT_BEP20_ADDRESS", "active": True, "reason": "", "min_amount": 1, "max_amount": 1000, "name": "USDT BEP20"},
                    "usdt_trc20": {"address": "USDT_TRC20_ADDRESS", "active": True, "reason": "", "min_amount": 1, "max_amount": 1000, "name": "USDT TRC20"},
                    "syriatelcash": {"address": "SYRIATELCASH_ADDRESS", "active": True, "reason": "", "min_amount": 1, "max_amount": 1000, "exchange_rate": 1, "name": "Syriatelcash"},
                    "vodafone_cash_egypt": {"address": "VODAFONE_CASH_EGYPT_ADDRESS", "active": True, "reason": "", "min_amount": 1, "max_amount": 1000, "exchange_rate": 1, "name": "Vodafone Cash Egypt"}
                },
                "exchange_rates": {"syrian_pound": 1, "egyptian_pound": 1},
                "servers": {"usa1": {"name": "🇺🇸 أمريكا 1", "endpoint": "https://iproxy.online/api/cn/v1/proxy-access", "api_key": "4bd8790b585b6d66081849b6670eb5ce601826aab1b1c8b7b814c5bfbd531c8e", "active": True}}
            }, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)

data = load_data()
bot = telebot.TeleBot(BOT_TOKEN)
user_sessions = {}

def update_balance(uid, amount):
    uid = str(uid)
    data["balance"][uid] = data["balance"].get(uid, 0) + amount
    if uid not in data["users"]:
        data["users"].append(uid)
    save_data(data)

def is_valid(value):
    return len(value) >= 12 and re.search(r"[A-Z]", value) and re.search(r"[0-9]", value)

def create_proxy(api_key, proxy_type, duration_minutes, username=None, password=None, ip=None, with_api=False, server_id="usa1"):
    # استخدام API key الخاص بالخادم إذا كان متوفراً، وإلا استخدم الافتراضي
    server_info = data["servers"].get(server_id, {})
    server_api_key = server_info.get("api_key", api_key)

    headers = {
        "Authorization": f"Bearer {server_api_key}",
        "Content-Type": "application/json"
    }

    has_api = with_api or proxy_type == "inject"

    # الحصول على endpoint الخادم المحدد
    server_endpoint = server_info.get("endpoint", "https://iproxy.online/api/cn/v1/proxy-access")

    expire_utc = datetime.utcnow() + timedelta(minutes=duration_minutes)
    expire_str = expire_utc.isoformat() + "Z"
    local_expire = (datetime.utcnow() + timedelta(minutes=duration_minutes, hours=3)).strftime('%Y-%m-%d %H:%M (GMT+3)')

    if proxy_type == "inject":
        payload = {
            "listen_service": "http",
            "auth_type": "noauth",
            "allow_from": [],
            "description": "inject proxy",
            "expired_at": expire_str
        }
    else:
        payload = {
            "listen_service": proxy_type,
            "auth_type": "userpass",
            "auth": {
                "login": username,
                "password": password
            },
            "description": f"{proxy_type} for {username}",
            "allow_from": [],
            "expired_at": expire_str
        }

    res = requests.post(server_endpoint, headers=headers, json=payload)
    if res.status_code == 200:
        result = res.json()
        return {
            "proxy_id": result.get("id"),
            "ip": result.get("ip"),
            "port": result.get("port"),
            "hostname": result.get("hostname"),
            "login": username,
            "password": password,
            "date_end": local_expire,
            "created": (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M (GMT+3)"),
            "type": proxy_type,
            "has_api": has_api,
            "server_id": server_id,
            "server_name": data["servers"].get(server_id, {}).get("name", "غير معروف")
        }
    else:
        return {"error": res.text}

def update_proxy_ip(proxy_id, new_ip, server_id=None):
    # الحصول على API key المناسب للخادم
    if server_id:
        server_info = data["servers"].get(server_id, {})
        api_key = server_info.get("api_key", data["api_key"])
    else:
        api_key = data["api_key"]

    url = f"https://iproxy.online/api/cn/v1/proxy-access/{proxy_id}/update"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/merge-patch+json"
    }
    payload = {
        "auth_type": "noauth",
        "allow_from": [new_ip]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            return {"success": True}
        return {"error": f"فشل التحديث: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"error": str(e)}

def can_change_ip(proxy, user_id):
    if not proxy.get("has_api"):
        return False, "هذا البروكسي لا يدعم تغيير IP"

    # الحصول على معرف الخادم للبروكسي الحالي
    current_server_id = proxy.get("server_id", "usa1")
    all_user_proxies = data["proxies"].get(user_id, [])

    # البحث عن آخر تغيير IP في نفس الخادم فقط
    latest_change = None
    for p in all_user_proxies:
        # التحقق من أن البروكسي من نفس الخادم
        if (p.get("has_api") and p.get("with_api") and 
            p.get("server_id", "usa1") == current_server_id):
            last_change = p.get("last_ip_change")
            if last_change:
                try:
                    change_time = datetime.fromisoformat(last_change)
                    if latest_change is None or change_time > latest_change:
                        latest_change = change_time
                except:
                    continue

    if latest_change:
        time_diff = datetime.now() - latest_change
        if time_diff.total_seconds() < 300:
            remaining = 300 - int(time_diff.total_seconds())
            server_name = data["servers"].get(current_server_id, {}).get("name", current_server_id)
            return False, f"⏳ يجب الانتظار {remaining} ثانية قبل تغيير IP مرة أخرى في خادم {server_name}"

    return True, None

def update_last_ip_change(proxy):
    proxy["last_ip_change"] = datetime.now().isoformat()
    save_data(data)

def calculate_remaining_minutes(proxy):
    try:
        end_date_str = proxy["date_end"]
        # إزالة (GMT+3) من النص
        end_date_clean = end_date_str.replace(" (GMT+3)", "")
        end_date = datetime.strptime(end_date_clean, "%Y-%m-%d %H:%M")
        
        # حساب المدة المتبقية بالدقائق مع مراعاة GMT+3
        # استخدام نفس المنطقة الزمنية المستخدمة في إنشاء البروكسي
        now_gmt3 = datetime.now() + timedelta(hours=3)
        time_remaining = end_date - now_gmt3
        minutes_remaining = max(1, int(time_remaining.total_seconds() / 60))
        
        return minutes_remaining
    except Exception as e:
        print(f"Error calculating remaining time: {e}")
        return 60  # إرجاع ساعة واحدة كحد أدنى في حالة الخطأ

def format_payment_methods():
    msg = "💳 طرق الدفع المتاحة:\n\n"
    for method_id, info in data["payment_methods"].items():
        if info["active"]:
            msg += f"💠 {info['name']}\n"
            msg += f"الحد الأدنى: {info['min_amount']}$\n"
            msg += f"الحد الأقصى: {info['max_amount']}$\n"
            if info.get("exchange_rate"):
                msg += f"سعر الصرف: {info['exchange_rate']}\n"
            msg += f"العنوان: `{info['address']}`\n\n"
    return msg

@bot.message_handler(commands=["start"])
def start(message):
    uid = str(message.from_user.id)
    if uid in data["banned"]:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📞 الدعم")
        return bot.send_message(message.chat.id, "تم الغاء خدمتك تلقائيا بسبب مخالفة الشروط", reply_markup=markup)
    update_balance(uid, 0)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 شراء بروكسي", "💰 رصيدي")
    markup.add("🔐 بروكسياتي", "💳 شحن الرصيد")
    markup.add("📞 الدعم")
    if uid == str(ADMIN_ID):
        markup.add("👥 إدارة المستخدمين")
        markup.add("💰 تحكم بنظام الإيداع")
        markup.add("💳 تحديث الأسعار", "🔄 تحديث API")
    welcome_msg = "👋 مرحباً بك في بوت البروكسي\n"
    welcome_msg += "━━━━━━━━━━━━━━\n"
    welcome_msg += "🔹 يمكنك شراء وإدارة البروكسيات\n"
    welcome_msg += "🔹 متابعة رصيدك وبروكسياتك\n"
    welcome_msg += "🔹 الحصول على الدعم الفني\n"
    welcome_msg += "━━━━━━━━━━━━━━\n"
    welcome_msg += "📝 اختر من القائمة أدناه:"
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def handle(message):
    uid = str(message.from_user.id)
    text = message.text.strip()
    if uid in data["banned"]:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📞 الدعم")
        msg = "تم الغاء خدمتك تلقائيا بسبب مخالفة الشروط\n"
        msg += "للتواصل مع الدعم الفني: @WorkTrekSupport"
        return bot.send_message(message.chat.id, msg, reply_markup=markup)
    sess = user_sessions.get(uid, {})

    clean_text = text
    for emoji in ["🔙 "]:
        clean_text = clean_text.replace(emoji, "")

    def set_step(uid, new_step):
        session = user_sessions.get(uid, {})
        session["previous_step"] = session.get("step")
        session["step"] = new_step
        user_sessions[uid] = session

    if text == "رجوع" or text == "🔙 رجوع":
        session = user_sessions.get(uid, {})
        prev = session.get("previous_step")
        current_step = session.get("step")

        # Menu hierarchy for admin menus
        menu_hierarchy = {
            "search_user": "admin_menu",
            "ban_user": "admin_menu",
            "update_price": "admin_menu",
            "balance_amount": "admin_menu",
            "select_user_delete_proxy": "admin_menu",
            "view_user_proxies": "admin_menu",
            "search_user_balance": "admin_menu",
            "select_user_balance": "admin_menu",
            "add_ip_url": "admin_menu",
            "update_api": "admin_menu",
            "payment_settings": "admin_menu", # added payment_settings
            "pending_deposits": "deposit_control",
            "manage_payment_methods": "deposit_control",
            "edit_exchange_rates": "deposit_control",
            "manage_servers": "admin_menu",
            "add_server": "manage_servers",
            "edit_server": "manage_servers",
            "delete_server": "manage_servers",
            "toggle_server": "manage_servers",
            "select_server_maintenance": "manage_servers",
            "select_replacement_server": "manage_servers"
        }

        admin_menus = {
            "admin_menu": {
                "markup": types.ReplyKeyboardMarkup(resize_keyboard=True).add("📊 إحصائيات عامة", "👥 قائمة المستخدمين").add("💳 إدارة الأرصدة", "⛔️ إدارة المحظورين").add("👥 إدارة بروكسيات المستخدمين", "⚙️ إدارة الخوادم").add("رجوع"),
                "message": "اختر من القائمة:"
            },
            "search_user": {
                "markup": types.ReplyKeyboardMarkup(resize_keyboard=True).add("🔍 بحث عن مستخدم").add("📋 عرض كل المستخدمين").add("رجوع"),
                "message": "اختر العملية:"
            },
            "ban_user": {
                "markup": types.ReplyKeyboardMarkup(resize_keyboard=True).add("📋 عرض المحظورين", "🚫 حظر مستخدم", "✅ فك الحظر").add("رجوع"),
                "message": "اختر من القائمة:"
            },
            "update_price": {
                "markup": types.ReplyKeyboardMarkup(resize_keyboard=True).add("تعديل سعر اليوم", "تعديل سعر الأسبوع", "تعديل سعر الشهر").add("رجوع"),
                "message": "اختر السعر المراد تعديله:"
            },
            "balance_amount": {
                "markup": types.ReplyKeyboardMarkup(resize_keyboard=True).add("➕ إضافة رصيد", "➖ إنقاص رصيد").add("رجوع"),
                "message": "اختر العملية:"
            },
            "select_user_delete_proxy": {
                "markup": types.ReplyKeyboardMarkup(resize_keyboard=True).add("قائمة بروكسيات المستخدم", "اختيار مستخدم للحذف").add("رجوع"),
                "message": "اختر من القائمة:"
            },
            "deposit_control": {
                "markup": types.ReplyKeyboardMarkup(resize_keyboard=True).add("📋 طلبات الإيداع المعلقة").add("⚙️ إدارة طرق الدفع").add("💱 تعديل أسعار الصرف").add("رجوع"),
                "message": "اختر من القائمة:"
            },
            "manage_servers": {
                "markup": types.ReplyKeyboardMarkup(resize_keyboard=True).add("📋 عرض الخوادم", "➕ إضافة خادم").add("✏️ تعديل خادم", "🗑️ حذف خادم").add("🔄 تفعيل/إلغاء خادم").add("رجوع"),
                "message": "اختر عملية إدارة الخوادم:"
            }
        }

        # If we're in proxy purchase flow
        if session.get("step") in ["type", "proxy_options", "duration", "username", "password", "ip"]:
            if session["step"] == "type":
                return start(message)
            elif session["step"] == "proxy_options":
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add("🌐 HTTP", "🔒 SOCKS5", "⚡ Inject", "🔙 رجوع")
                session["step"] = "type"
                user_sessions[uid] = session
                return bot.send_message(message.chat.id, "اختر نوع البروكسي:", reply_markup=markup)
            elif session["step"] == "duration":
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add("🌐 HTTP", "🔒 SOCKS5", "⚡ Inject", "🔙 رجوع")
                session["step"] = "type"
                user_sessions[uid] = session
                return bot.send_message(message.chat.id, "اختر نوع البروكسي:", reply_markup=markup)
            elif session["step"] == "duration_advanced":
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add("بروكسي عادي", "بروكسي مع تغيير IP")
                markup.add("رجوع")
                session["step"] = "proxy_options"
                user_sessions[uid] = session
                return bot.send_message(message.chat.id, "اختر نوع البروكسي:", reply_markup=markup)
            elif session["step"] in ["username", "ip"]:
                price_multiplier = 1.5 if session.get("with_api") else 1
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add(
                    f"يوم: {data['prices']['day'] * price_multiplier}$",
                    f"أسبوع: {data['prices']['week'] * price_multiplier}$",
                    "رجوع"
                )
                session["step"] = "duration"
                user_sessions[uid] = session
                return bot.send_message(message.chat.id, "اختر المدة:", reply_markup=markup)
            elif session["step"] == "password":
                session["step"] = "username"
                user_sessions[uid] = session
                return bot.send_message(message.chat.id, "أدخل اسم المستخدم:")

        # معالجة الرجوع في القوائم الإدارية
        elif current_step in menu_hierarchy:
            previous_menu = menu_hierarchy[current_step]
            if previous_menu is None:
                return start(message)

            menu_config = admin_menus.get(previous_menu)
            if menu_config:
                session["step"] = previous_menu
                user_sessions[uid] = session
                return bot.send_message(
                    message.chat.id,
                    menu_config["message"],
                    reply_markup=menu_config["markup"]
                )

        # For other menus, use the previous logic
        if not prev:
            return start(message)

        session["step"] = prev
        user_sessions[uid] = session

        step_responses = {
            "type": {
                "markup": types.ReplyKeyboardMarkup(resize_keyboard=True).add("🌐 HTTP", "🔒 SOCKS5", "⚡ Inject", "🔙 رجوع"),
                "message": "اختر نوع البروكسي:"
            },
            "proxy_options": {
                "markup": types.ReplyKeyboardMarkup(resize_keyboard=True).add("بروكسي عادي", "بروكسي مع تغيير IP").add("رجوع"),
                "message": "اختر نوع البروكسي:"
            },
            "duration": {
                "markup": types.ReplyKeyboardMarkup(resize_keyboard=True).add(
                    f"3 ساعات: {data['prices']['3hours'] * (1.5 if session.get('with_api') else 1)}$",
                    f"12 ساعة: {data['prices']['12hours'] * (1.5 if session.get('with_api') else 1)}$"
                ).add(
                    f"يوم: {data['prices']['day'] * (1.5 if session.get('with_api') else 1)}$",
                    f"أسبوع: {data['prices']['week'] * (1.5 if session.get('with_api') else 1)}$"
                ).add(
                    f"شهر: {data['prices']['month'] * (1.5 if session.get('with_api') else 1)}$",
                    "رجوع"
                ),
                "message": "اختر المدة:"
            },
            "username": {
                "message": "أدخل اسم المستخدم:"
            },
            "password": {
                "message": "أدخل كلمة المرور:"
            },
            "ip": {
                "message": "أرسل عنوان الـIP:"
            },
            "search_user": {
                "markup": types.ReplyKeyboardMarkup(resize_keyboard=True).add("🔍 بحث عن مستخدم").add("📋 عرض كل المستخدمين").add("رجوع"),
                "message": "اختر العملية:"
            },
            "ban_user": {
                "markup": types.ReplyKeyboardMarkup(resize_keyboard=True).add("📋 عرض المحظورين", "🚫 حظر مستخدم", "✅ فك الحظر").add("رجوع"),
                "message": "اختر من القائمة:"
            },
            "update_price": {
                "markup": types.ReplyKeyboardMarkup(resize_keyboard=True).add("تعديل سعر اليوم", "تعديل سعر الأسبوع", "تعديل سعر الشهر").add("رجوع"),
                "message": "اختر السعر المراد تعديله:"
            },
            "balance_amount": {
                "markup": types.ReplyKeyboardMarkup(resize_keyboard=True).add("➕ إضافة رصيد", "➖ إنقاص رصيد").add("رجوع"),
                "message": "اختر العملية:"
            },
            "select_user_delete_proxy": {
                "markup": types.ReplyKeyboardMarkup(resize_keyboard=True).add("قائمة بروكسيات المستخدم", "اختيار مستخدم للحذف").add("رجوع"),
                "message": "اختر من القائمة:"
            },
            "admin_menu": {
                "markup": types.ReplyKeyboardMarkup(resize_keyboard=True).add("📊 إحصائيات عامة", "👥 قائمة المستخدمين").add("💳 إدارة الأرصدة", "⛔️ إدارة المحظورين").add("👥 إدارة بروكسيات المستخدمين").add("رجوع"),
                "message": "اختر من القائمة:"
            },
            "deposit_control": {
                "markup": types.ReplyKeyboardMarkup(resize_keyboard=True).add("📋 طلبات الإيداع المعلقة").add("⚙️ إدارة طرق الدفع").add("💱 تعديل أسعار الصرف").add("رجوع"),
                "message": "اختر من القائمة:"
            },
            "manage_servers": {
                "markup": types.ReplyKeyboardMarkup(resize_keyboard=True).add("📋 عرض الخوادم", "➕ إضافة خادم").add("✏️ تعديل خادم", "🗑️ حذف خادم").add("🔄 تفعيل/إلغاء خادم").add("رجوع"),
                "message": "اختر عملية إدارة الخوادم:"
            }
        }

        response = step_responses.get(prev, {"message": "اختر من القائمة:", "markup": None})
        if response["markup"]:
            return bot.send_message(message.chat.id, response["message"], reply_markup=response["markup"])
        elif response["message"]:
            return bot.send_message(message.chat.id, response["message"])

        return start(message)

    clean_text = text.replace("💰 ", "").replace("🔐 ", "").replace("📞 ", "")

    if clean_text == "رصيدي":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("رجوع")
        return bot.send_message(message.chat.id, f"رصيدك: {data['balance'].get(uid, 0)}$", reply_markup=markup)

    if clean_text == "بروكسياتي":
        proxies = data.get("proxies", {}).get(uid, [])
        if not proxies:
            return bot.send_message(message.chat.id, "لا تملك بروكسيات.")

    if text == "💳 شحن الرصيد":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        crypto_methods = []
        for method_id, info in data["payment_methods"].items():
            if info["active"]:
                if method_id in ["ltc", "trx", "usdt_trc20", "usdt_bep20"]:
                    if method_id not in ["usdt_trc20", "usdt_bep20"]:
                        crypto_methods.append(info["name"])
                else:
                    markup.add(f"💳 {info['name']}")
        if crypto_methods:
            markup.add("💰 Crypto")
        markup.add("رجوع")
        user_sessions[uid] = {"step": "select_payment_method"}
        return bot.send_message(message.chat.id, "اختر طريقة الدفع:", reply_markup=markup)

    if text == "💰 Crypto":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("💳 LTC", "💳 TRX", "💳 USDT")
        markup.add("رجوع")
        user_sessions[uid] = {"step": "select_crypto_method"}
        return bot.send_message(message.chat.id, "اختر العملة:", reply_markup=markup)

    if text == "💳 USDT":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("💳 USDT TRC20", "💳 USDT BEP20")
        markup.add("رجوع")
        user_sessions[uid] = {"step": "select_usdt_network"}
        return bot.send_message(message.chat.id, "اختر الشبكة:", reply_markup=markup)

    if sess.get("step") == "select_crypto_method":
        if text == "💳 LTC":
            sess["payment_method"] = "ltc"
            selected_method = data["payment_methods"]["ltc"]
        elif text == "💳 TRX":
            sess["payment_method"] = "trx"
            selected_method = data["payment_methods"]["trx"]
        elif text == "💳 USDT":
            return
        else:
            return

        sess["step"] = "enter_amount"
        msg = f"💰 أدخل المبلغ المراد إيداعه\n"
        msg += "━━━━━━━━━━━━━━\n"
        msg += f"الحد الأدنى: {selected_method['min_amount']}$\n"
        msg += f"الحد الأقصى: {selected_method['max_amount']}$"
        if selected_method.get("exchange_rate"):
            msg += f"\nسعر الصرف: {selected_method['exchange_rate']}"
        return bot.send_message(message.chat.id, msg)

    if sess.get("step") == "select_usdt_network":
        network = None
        if text == "💳 USDT TRC20":
            sess["payment_method"] = "usdt_trc20"
            selected_method = data["payment_methods"]["usdt_trc20"]
        elif text == "💳 USDT BEP20":
            sess["payment_method"] = "usdt_bep20"
            selected_method = data["payment_methods"]["usdt_bep20"]
        else:
            return

        sess["step"] = "enter_amount"
        msg = f"💰 أدخل المبلغ المراد إيداعه\n"
        msg += "━━━━━━━━━━━━━━\n"
        msg += f"الحد الأدنى: {selected_method['min_amount']}$\n"
        msg += f"الحد الأقصى: {selected_method['max_amount']}$"
        if selected_method.get("exchange_rate"):
            msg += f"\nسعر الصرف: {selected_method['exchange_rate']}"
        return bot.send_message(message.chat.id, msg)

    if sess.get("step") == "select_payment_method" and text.startswith("💳 "):
        method_name = text[2:]
        selected_method = None
        for method_id, info in data["payment_methods"].items():
            if info["name"] == method_name and method_id not in ["ltc", "trx", "usdt_trc20", "usdt_bep20"]:
                selected_method = info
                sess["payment_method"] = method_id
                break

        if selected_method:
            sess["step"] = "enter_amount"
            msg = f"💰 أدخل المبلغ المراد إيداعه\n"
            msg += "━━━━━━━━━━━━━━\n"
            msg += f"الحد الأدنى: {selected_method['min_amount']}$\n"
            msg += f"الحد الأقصى: {selected_method['max_amount']}$\n"
            if method_id == "vodafone_cash_egypt":
                egyptian_rate = data["exchange_rates"].get("egyptian_pound", 1)
                msg += f"سعر الصرف: {egyptian_rate} جنيه مصري للدولار"
            elif method_id == "syriatelcash":
                syrian_rate = data["exchange_rates"].get("syrian_pound", 1)
                msg += f"سعر الصرف: {syrian_rate} ليرة سورية للدولار"
            return bot.send_message(message.chat.id, msg)

    if sess.get("step") == "enter_amount":
        try:
            amount = float(text)
            method = data["payment_methods"][sess["payment_method"]]
            method_id = sess["payment_method"]

            if amount < method["min_amount"] or amount > method["max_amount"]:
                return bot.send_message(message.chat.id, f"المبلغ يجب أن يكون بين {method['min_amount']}$ و {method['max_amount']}$")

            msg = "📝 معلومات الإيداع:\n"
            msg += "━━━━━━━━━━━━━━\n"
            msg += f"💰 المبلغ: {amount}$\n"

            # عرض سعر الصرف للفودافون كاش
            if method_id == "vodafone_cash_egypt":
                egyptian_rate = data["exchange_rates"].get("egyptian_pound", 1)
                msg += f"💱 سعر الصرف: {egyptian_rate} جنيه مصري\n"

            # تحويل العملة حسب طريقة الدفع
            if sess["payment_method"] == "syriatelcash":
                syrian_rate = data["exchange_rates"].get("syrian_pound", 1)
                syrian_amount = amount * syrian_rate
                msg += f"💵 المبلغ بالليرة السورية: {syrian_amount:,.0f} ل.س\n"
            elif sess["payment_method"] == "vodafone_cash_egypt":
                egyptian_rate = data["exchange_rates"].get("egyptian_pound", 1)
                egyptian_amount = amount * egyptian_rate
                msg += f"💵 المبلغ بالجنيه المصري: {egyptian_amount:,.0f} ج.م\n"

            msg += f"💳 طريقة الدفع: {method['name']}\n"
            msg += f"📇 عنوان الدفع: `{method['address']}`\n"
            msg += "━━━━━━━━━━━━━━\n"
            msg += "✅ قم بتحويل المبلغ ثم أرسل معرف عملية التحويل"

            sess["amount"] = amount
            sess["step"] = "waiting_transaction_id"
            return bot.send_message(message.chat.id, msg, parse_mode="Markdown")

        except ValueError:
            return bot.send_message(message.chat.id, "الرجاء إدخال مبلغ صحيح")

    if sess.get("step") == "waiting_transaction_id":
        transaction_id = text.strip()

        # حفظ معرف العملية مؤقتاً وطلب التأكيد
        sess["temp_transaction_id"] = transaction_id
        sess["step"] = "confirm_transaction"

        msg = "📝 تأكيد معلومات الإيداع:\n"
        msg += "━━━━━━━━━━━━━━\n"
        msg += f"💰 المبلغ: {sess['amount']}$\n"
        msg += f"💳 طريقة الدفع: {data['payment_methods'][sess['payment_method']]['name']}\n"
        msg += f"🧾 معرف العملية: {transaction_id}\n"
        msg += "━━━━━━━━━━━━━━\n"
        msg += "هل أنت متأكد من صحة المعلومات؟"

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("✅ نعم، متأكد", "❌ لا، إلغاء")
        return bot.send_message(message.chat.id, msg, reply_markup=markup)

    if sess.get("step") == "confirm_transaction":
        if text == "✅ نعم، متأكد":
            transaction_id = sess["temp_transaction_id"]
            deposit_id = str(int(time.time()))
            if "pending_deposits" not in data:
                data["pending_deposits"] = {}

            data["pending_deposits"][deposit_id] = {
                "user_id": uid,
                "amount": sess["amount"],
                "method": sess["payment_method"],
                "status": "pending",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "payment_address": data["payment_methods"][sess["payment_method"]]["address"],
                "transaction_id": transaction_id
            }
            save_data(data)

            # إرسال إشعار للمشرف
            admin_msg = "🔔 طلب إيداع جديد!\n"
            admin_msg += "━━━━━━━━━━━━━━\n"
            admin_msg += f"💰 المبلغ: {sess['amount']}$\n"
            admin_msg += f"💳 طريقة الدفع: {data['payment_methods'][sess['payment_method']]['name']}\n"
            admin_msg += f"👤 معرف المستخدم: {uid}\n"
            admin_msg += f"🧾 معرف العملية: {transaction_id}\n"
            admin_msg += f"📇 رقم الطلب: {deposit_id}"

            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ قبول", callback_data=f"approve_deposit:{deposit_id}"),
                types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_deposit:{deposit_id}")
            )
            bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)

            msg = "✅ تم استلام طلب الإيداع\n"
            msg += "━━━━━━━━━━━━━━\n"
            msg += "طلبك قيد المعالجة من قبل الإدارة\n"
            msg += "يرجى الانتظار بصبر\n"
            msg += "━━━━━━━━━━━━━━\n"
            msg += f"🧾 رقم الطلب: {deposit_id}"

            user_sessions.pop(uid)
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("🛒 شراء بروكسي", "💰 رصيدي")
            markup.add("🔐 بروكسياتي", "💳 شحن الرصيد")
            markup.add("📞 الدعم")
            if uid == str(ADMIN_ID):
                markup.add("👥 إدارة المستخدمين")
                markup.add("💰 تحكم بنظام الإيداع")
                markup.add("💳 تحديث الأسعار", "🔄 تحديث API")
            return bot.send_message(message.chat.id, msg, reply_markup=markup)

        elif text == "❌ لا، إلغاء":
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("🛒 شراء بروكسي", "💰 رصيدي")
            markup.add("🔐 بروكسياتي", "💳 شحن الرصيد")
            markup.add("📞 الدعم")
            if uid == str(ADMIN_ID):
                markup.add("👥 إدارة المستخدمين")
                markup.add("💰 تحكم بنظام الإيداع")
                markup.add("💳 تحديث الأسعار", "🔄 تحديث API")
            user_sessions.pop(uid)
            return bot.send_message(message.chat.id, "تم إلغاء عملية الإيداع", reply_markup=markup)
        else:
            return bot.send_message(message.chat.id, "الرجاء اختيار نعم أو لا")

        # إرسال إشعار للمشرف
        admin_msg = "🔔 طلب إيداع جديد!\n"
        admin_msg += "━━━━━━━━━━━━━━\n"
        admin_msg += f"💰 المبلغ: {sess['amount']}$\n"
        admin_msg += f"💳 طريقة الدفع: {data['payment_methods'][sess['payment_method']]['name']}\n"
        admin_msg += f"👤 معرف المستخدم: {uid}\n"
        admin_msg += f"🧾 معرف العملية: {transaction_id}\n"
        admin_msg += f"📇 رقم الطلب: {deposit_id}"

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ قبول", callback_data=f"approve_deposit:{deposit_id}"),
            types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_deposit:{deposit_id}")
        )
        bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)

        msg = "✅ تم استلام طلب الإيداع\n"
        msg += "━━━━━━━━━━━━━━\n"
        msg += "طلبك قيد المعالجة من قبل الإدارة\n"
        msg += "يرجى الانتظار بصبر\n"
        msg += "━━━━━━━━━━━━━━\n"
        msg += f"🧾 رقم الطلب: {deposit_id}"

        user_sessions.pop(uid)
        return bot.send_message(message.chat.id, msg)

    if text == "الدعم" or text == "📞 الدعم":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("تواصل مع الدعم", url="https://t.me/WorkTrekSupport"))
        if uid in data["banned"]:
            return bot.send_message(message.chat.id, "تم الغاء خدمتك تلقائيا بسبب مخالفة الشروط\nللتواصل مع الدعم الفني اضغط على الزر أدناه:", reply_markup=markup)
        return bot.send_message(message.chat.id, "للتواصل مع الدعم الفني اضغط على الزر أدناه:", reply_markup=markup)

    if text == "رصيدي":
        return bot.send_message(message.chat.id, f"رصيدك: {data['balance'].get(uid, 0)}$")

    # Remove all emojis for text matching
    clean_menu_text = text
    emoji_list = ["🛒 ", "💰 ", "🔐 ", "📞 ", "👥 ", "💳 ", "🔄 ", "📊 ", "⛔️ ", "✅ ", "➕ ", "➖ ", "🔍 ", "📋 ", "🌐 ", "🔒 ", "⚡ ", "🔙 "]
    for emoji in emoji_list:
        clean_menu_text = clean_menu_text.replace(emoji, "")

    # Check both original and clean text for all commands
    if clean_menu_text == "بروكسياتي" or text == "🔐 بروكسياتي":
        proxies = data.get("proxies", {}).get(uid, [])
        if not proxies:
            return bot.send_message(message.chat.id, "لا تملك بروكسيات.")

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("عرض البروكسيات")
        markup.add("رجوع")
        return bot.send_message(message.chat.id, "اختر من القائمة:", reply_markup=markup)

    if text == "عرض البروكسيات":
        proxies = data.get("proxies", {}).get(uid, [])
        if not proxies:
            return bot.send_message(message.chat.id, "لا تملك بروكسيات.")

        markup = types.InlineKeyboardMarkup(row_width=1)
        for i, p in enumerate(sorted(proxies, key=lambda x: x["created"], reverse=True), 1):
            button_text = f"🔐 بروكسي {p['type'].upper()} - {p['port']}"
            if p.get('has_api'):
                button_text += " 🔄"
            markup.add(types.InlineKeyboardButton(
                button_text,
                callback_data=f"view_proxy:{p['proxy_id']}"
            ))
        return bot.send_message(message.chat.id, "📋 اختر بروكسي لعرض معلوماته:", reply_markup=markup)
        return bot.send_message(message.chat.id, msg, parse_mode="Markdown")

    clean_text = text
    for emoji in ["👥 ", "📊 ", "💳 ", "⛔️ ", "🔙 "]:
        clean_text = clean_text.replace(emoji, "")

    if text == "👥 إدارة المستخدمين" and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📊 إحصائيات عامة", "👥 قائمة المستخدمين")
        markup.add("💳 إدارة الأرصدة", "⛔️ إدارة المحظورين")
        markup.add("👥 إدارة بروكسيات المستخدمين", "⚙️ إدارة الخوادم")
        markup.add("رجوع")
        sess = user_sessions.get(uid, {})
        sess["step"] = "admin_menu"
        user_sessions[uid] = sess
        return bot.send_message(message.chat.id, "اختر من القائمة:", reply_markup=markup)

    if (text == "إحصائيات عامة" or text == "📊 إحصائيات عامة") and uid == str(ADMIN_ID):
        total_users = len(data["users"])
        total_balance = sum(data["balance"].values())
        active_proxies = sum(len(proxies) for proxies in data["proxies"].values())
        stats = "📊 إحصائيات عامة:\n\n"
        stats += f"👥 إجمالي المستخدمين: {total_users}\n"
        stats += f"💰 إجمالي الرصيد: {total_balance}$\n"
        stats += f"🔐 البروكسيات النشطة: {active_proxies}\n"
        stats += f"🚫 المستخدمين المحظورين: {len(data['banned'])}"
        return bot.send_message(message.chat.id, stats)

    clean_admin_text = text
    for emoji in ["⛔️ ", "📋 ", "🚫 ", "✅ "]:
        clean_admin_text = clean_admin_text.replace(emoji, "")

    if (text == "⛔️ إدارة المحظورين" or clean_admin_text == "إدارة المحظورين") and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📋 عرض المحظورين", "🚫 حظر مستخدم", "✅ فك الحظر")
        markup.add("رجوع")
        return bot.send_message(message.chat.id, "اختر من القائمة:", reply_markup=markup)

    if (text == "📋 عرض المحظورين" or clean_text == "عرض المحظورين") and uid == str(ADMIN_ID):
        if not data["banned"]:
            return bot.send_message(message.chat.id, "لا يوجد مستخدمين محظورين")

        stats = "⛔️ قائمة المستخدمين المحظورين:\n\n"
        for banned_id in data["banned"]:
            try:
                user = bot.get_chat(int(banned_id))
                name = user.first_name if user else "غير معروف"
                stats += f"• {name}\n  ID: {banned_id}\n\n"
            except:
                continue
        return bot.send_message(message.chat.id, stats)

    if text == "👥 قائمة المستخدمين" and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🔍 بحث عن مستخدم")
        markup.add("📋 عرض كل المستخدمين")
        markup.add("رجوع")
        return bot.send_message(message.chat.id, "اختر العملية:", reply_markup=markup)

    if text == "🔍 بحث عن مستخدم" and uid == str(ADMIN_ID):
        user_sessions[uid] = {"step": "search_user"}
        return bot.send_message(message.chat.id, "أرسل معرف المستخدم أو اسمه للبحث:")

    if text == "📋 عرض كل المستخدمين" and uid == str(ADMIN_ID):
        markup = types.InlineKeyboardMarkup(row_width=1)
        for user_id in data["users"]:
            try:
                user = bot.get_chat(int(user_id))
                if user:
                    name = user.first_name or "غير معروف"
                    username = f"@{user.username}" if user.username else "لا يوجد معرف"
                    button_text = f"{name} | {username}"
                    callback_data = f"user_info:{user_id}"
                    markup.add(types.InlineKeyboardButton(text=button_text, callback_data=callback_data))
            except:
                continue
        return bot.send_message(message.chat.id, "قائمة المستخدمين:", reply_markup=markup)

    if sess.get("step") == "search_user":
        search_term = text.lower()
        found_users = []
        markup = types.InlineKeyboardMarkup(row_width=1)

        for user_id in data["users"]:
            try:
                user = bot.get_chat(int(user_id))
                if user:
                    name = (user.first_name or "").lower()
                    username = (user.username or "").lower()
                    if search_term in name or search_term in username or search_term == str(user_id):
                        button_text = f"{user.first_name or 'غير معروف'} | @{user.username or 'لا يوجد معرف'}"
                        callback_data = f"user_info:{user_id}"
                        markup.add(types.InlineKeyboardButton(text=button_text, callback_data=callback_data))
                        found_users.append(user_id)
            except:
                continue

        user_sessions.pop(uid, None)
        if not found_users:
            return bot.send_message(message.chat.id, "لم يتم العثور على أي مستخدم.")
        return bot.send_message(message.chat.id, "المستخدمون الذين تم العثور عليهم:", reply_markup=markup)

    if text == "👥 إدارة بروكسيات المستخدمين" and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("قائمة بروكسيات المستخدم", "اختيار مستخدم للحذف")
        markup.add("إضافة رابط جديد لتغيير IP")
        markup.add("رجوع")
        return bot.send_message(message.chat.id, "اختر من القائمة:", reply_markup=markup)

    if text == "اختيار مستخدم للحذف" and uid == str(ADMIN_ID):
        user_sessions[uid] = {"step": "select_user_delete_proxy"}
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for user_id in data["users"]:
            if data.get("proxies", {}).get(user_id, []):
                try:
                    user = bot.get_chat(int(user_id))
                    name = user.first_name if user else str(user_id)
                    markup.add(f"{name} - {user_id}")
                except:
                    continue
        markup.add("رجوع")
        return bot.send_message(message.chat.id, "اختر المستخدم:", reply_markup=markup)

    if text == "قائمة بروكسيات المستخدم" and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for user_id in data["users"]:
            proxies = data.get("proxies", {}).get(user_id, [])
            if proxies:
                try:
                    user = bot.get_chat(int(user_id))
                    name = user.first_name if user else str(user_id)
                    markup.add(f"{name} - {user_id}")
                except:
                    continue
        markup.add("رجوع")
        user_sessions[uid] = {"step": "view_user_proxies"}
        return bot.send_message(message.chat.id, "اختر المستخدم لعرض بروكسياته:", reply_markup=markup)

    if sess.get("step") == "view_user_proxies" and " - " in text:
        try:
            target_id = text.split(" - ")[1]
            proxies = data.get("proxies", {}).get(target_id, [])
            if not proxies:
                return bot.send_message(message.chat.id, "لا يوجد بروكسيات لهذا المستخدم.")

            msg = "📋 بروكسيات المستخدم:\n\n"
            for p in proxies:
                msg += f"• نوع البروكسي: {p['type'].upper()}\n"
                msg += f"  IP: {p['ip']}\n"
                msg += f"  Port: {p['port']}\n"
                if p.get('login'):
                    msg += f"  Username: {p['login']}\n"
                    msg += f"  Password: {p['password']}\n"
                msg += f"  ينتهي في: {p['date_end']}\n"
                msg += "───────────────\n"

            return bot.send_message(message.chat.id, msg)
        except:
            return bot.send_message(message.chat.id, "خطأ في عرض بروكسيات المستخدم.")

    if (clean_menu_text == "تحديث الأسعار" or text == "💳 تحديث الأسعار") and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("تعديل سعر 3 ساعات", "تعديل سعر 12 ساعة")
        markup.add("تعديل سعر اليوم", "تعديل سعر الأسبوع")
        markup.add("تعديل سعر الشهر")
        markup.add("تعديل سعر الأسبوع مع API", "تعديل سعر الشهر مع API")
        markup.add("رجوع")
        msg = "📊 الأسعار الحالية:\n"
        msg += "━━━━━━━━━━━━━━\n"
        msg += "🔹 البروكسي العادي:\n"
        msg += f"3 ساعات: {data['prices']['3hours']}$\n"
        msg += f"12 ساعة: {data['prices']['12hours']}$\n"
        msg += f"يوم: {data['prices']['day']}$\n"
        msg += f"أسبوع: {data['prices']['week']}$\n"
        msg += f"شهر: {data['prices']['month']}$\n"
        msg += "━━━━━━━━━━━━━━\n"
        msg += "🔹 البروكسي مع تغيير IP:\n"
        msg += f"أسبوع: {data['prices']['week_api']}$\n"
        msg += f"شهر: {data['prices']['month_api']}$\n"
        msg += "\nاختر السعر المراد تعديله:"
        return bot.send_message(message.chat.id, msg, reply_markup=markup)

    if text in ["تعديل سعر 3 ساعات", "تعديل سعر 12 ساعة", "تعديل سعر اليوم", "تعديل سعر الأسبوع", "تعديل سعر الشهر", "تعديل سعر الأسبوع مع API", "تعديل سعر الشهر مع API"]:
        period = {
            "تعديل سعر 3 ساعات": "3hours", 
            "تعديل سعر 12 ساعة": "12hours",
            "تعديل سعر اليوم": "day", 
            "تعديل سعر الأسبوع": "week", 
            "تعديل سعر الشهر": "month",
            "تعديل سعر الأسبوع مع API": "week_api",
            "تعديل سعر الشهر مع API": "month_api"
        }[text]
        user_sessions[uid] = {"step": "update_price", "period": period}
        return bot.send_message(message.chat.id, f"أدخل السعر الجديد لـ {text.replace('تعديل سعر ', '')}:")

    if sess.get("step") == "update_price":
        try:
            price = float(text)
            period = sess["period"]
            data["prices"][period] = price
            save_data(data)
            user_sessions.pop(uid)
            return bot.send_message(message.chat.id, f"تم تحديث السعر بنجاح إلى {price}$")
        except:
            return bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح")

    if text == "🚫 حظر مستخدم" and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for user_id in data["users"]:
            try:
                user = bot.get_chat(int(user_id))
                name = user.first_name if user else str(user_id)
                if user_id != str(ADMIN_ID):
                    markup.add(f"{name} - {user_id}")
            except:
                continue
        markup.add("رجوع")
        user_sessions[uid] = {"step": "ban_user"}
        return bot.send_message(message.chat.id, "اختر المستخدم للحظر:", reply_markup=markup)

    if text == "✅ فك الحظر" and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for banned_id in data["banned"]:
            try:
                user = bot.get_chat(int(banned_id))
                name = user.first_name if user else str(banned_id)
                markup.add(f"{name} - {banned_id}")
            except:
                continue
        markup.add("رجوع")
        user_sessions[uid] = {"step": "unban_user"}
        return bot.send_message(message.chat.id, "اختر المستخدم لفك الحظر:", reply_markup=markup)

    if sess.get("step") == "ban_user" and " - " in text:
        try:
            target_id = text.split(" - ")[1]
            if target_id == str(ADMIN_ID):
                return bot.send_message(message.chat.id, "لا يمكن حظر المشرف.")
            if target_id not in data["banned"]:
                data["banned"].append(target_id)
                save_data(data)
                try:
                    bot.send_message(int(target_id), "تم الغاء خدمتك تلقائيا بسبب مخالفة الشروط يرجى التواصل مع الدعم من الزر الدعم ")
                except:
                    pass
            user_sessions.pop(uid)
            return bot.send_message(message.chat.id, f"تم حظر المستخدم {target_id}")
        except:
            return bot.send_message(message.chat.id, "خطأ في اختيار المستخدم.")

    if sess.get("step") == "unban_user" and " - " in text:
        try:
            target_id = text.split(" - ")[1]
            if target_id in data["banned"]:
                data["banned"].remove(target_id)
                save_data(data)
            user_sessions.pop(uid)
            return bot.send_message(message.chat.id, f"تم فك حظر المستخدم {target_id}")
        except:
            return bot.send_message(message.chat.id, "خطأ في اختيار المستخدم.")

    if (text == "💳 إدارة الأرصدة" or clean_text == "إدارة الأرصدة") and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🔍 بحث عبر الآيدي", "📋 عرض القائمة")
        markup.add("رجوع")
        return bot.send_message(message.chat.id, "اختر طريقة البحث:", reply_markup=markup)

    if text == "📋 عرض القائمة" and uid == str(ADMIN_ID):
        user_sessions[uid] = {"step": "select_user_balance"}
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for user_id in data["users"]:
            try:
                user = bot.get_chat(int(user_id))
                name = user.first_name if user else str(user_id)
                balance = data["balance"].get(user_id, 0)
                markup.add(f"{name} - {balance}$ - {user_id}")
            except:
                continue
        markup.add("رجوع")
        return bot.send_message(message.chat.id, "اختر المستخدم:", reply_markup=markup)

    if text == "🔍 بحث عبر الآيدي" and uid == str(ADMIN_ID):
        user_sessions[uid] = {"step": "search_user_balance"}
        return bot.send_message(message.chat.id, "أدخل آيدي المستخدم:")

    if sess.get("step") == "search_user_balance":
        try:
            target_id = str(int(text))
            if target_id not in data["users"]:
                return bot.send_message(message.chat.id, "المستخدم غير موجود.")

            user = bot.get_chat(int(target_id))
            name = user.first_name if user else "غير معروف"
            balance = data["balance"].get(target_id, 0)

            stats = f"معلومات المستخدم:\n\n"
            stats += f"• الاسم: {name}\n"
            stats += f"• الآيدي: {target_id}\n"
            stats += f"• الرصيد: {balance}$\n"

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("➕ إضافة رصيد", "➖ إنقاص رصيد")
            markup.add("رجوع")

            user_sessions[uid] = {"target_id": target_id}
            return bot.send_message(message.chat.id, stats, reply_markup=markup)
        except:
            return bot.send_message(message.chat.id, "معرف غير صالح.")

    if " - " in text and sess.get("step") == "select_user_balance":
        try:
            target_id = text.split(" - ")[2]
            if target_id not in data["users"]:
                return bot.send_message(message.chat.id, "المستخدم غير موجود.")

            user = bot.get_chat(int(target_id))
            name = user.first_name if user else "غير معروف"
            balance = data["balance"].get(target_id, 0)

            stats = f"معلومات المستخدم:\n\n"
            stats += f"• الاسم: {name}\n"
            stats += f"• الآيدي: {target_id}\n"
            stats += f"• الرصيد: {balance}$\n"

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("➕ إضافة رصيد", "➖ إنقاص رصيد")
            markup.add("رجوع")

            user_sessions[uid] = {"target_id": target_id, "step": "balance_action"}
            return bot.send_message(message.chat.id, stats, reply_markup=markup)
        except Exception as e:
            return bot.send_message(message.chat.id, f"خطأ في اختيار المستخدم: {e}")

    if text in ["➕ إضافة رصيد", "➖ إنقاص رصيد"] and uid == str(ADMIN_ID):
        user_sessions[uid]["step"] = "balance_amount"
        user_sessions[uid]["action"] = "add" if text.startswith("➕") else "subtract"
        return bot.send_message(message.chat.id, "أدخل المبلغ:")

    if sess.get("step") == "balance_user":
        try:
            target_id = str(int(text))
            if target_id not in data["users"]:
                return bot.send_message(message.chat.id, "المستخدم غير موجود.")
            sess["target_id"] = target_id
            sess["step"] = "balance_amount"
            return bot.send_message(message.chat.id, "أدخل المبلغ:")
        except:
            return bot.send_message(message.chat.id, "معرف غير صالح.")

    if sess.get("step") == "balance_amount":
        try:
            amount = float(text)
            if amount <= 0:
                return bot.send_message(message.chat.id, "يجب أن يكون المبلغ أكبر من صفر.")
            sess["amount"] = amount
            sess["step"] = "balance_note"
            return bot.send_message(message.chat.id, "أدخل ملاحظة للمستخدم:")
        except:
            return bot.send_message(message.chat.id, "مبلغ غير صالح.")

    if sess.get("step") == "delete_proxy_note":
        if text == "نعم":
            sess["step"] = "send_delete_note"
            return bot.send_message(message.chat.id, "أدخل الملاحظة التي تريد إرسالها للمستخدم:")
        elif text == "لا":
            target_id = sess["target_id"]
            proxy_id = sess["proxy_id"]
            proxies = sess["proxies_backup"]
            data["proxies"][target_id] = [p for p in proxies if str(p.get("proxy_id")) != proxy_id]
            save_data(data)
            user_sessions.pop(uid)
            return bot.send_message(message.chat.id, "تم حذف البروكسي بنجاح.")

    if sess.get("step") == "send_delete_note":
        note = text.strip()
        target_id = sess["target_id"]
        proxy_id = sess["proxy_id"]
        proxies = sess["proxies_backup"]
        data["proxies"][target_id] = [p for p in proxies if str(p.get("proxy_id")) != proxy_id]
        save_data(data)
        try:
            bot.send_message(int(target_id), f"تم حذف البروكسي الخاص بك.\nملاحظة من الإدارة: {note}")
        except:
            pass
        user_sessions.pop(uid)
        return bot.send_message(message.chat.id, "تم حذف البروكسي وإرسال الملاحظة بنجاح.")

    if sess.get("step") == "balance_note":
        note = text.strip()
        target_id = sess["target_id"]
        amount = sess["amount"]
        if sess["action"] == "subtract":
            amount = -amount

        update_balance(target_id, amount)
        action_text = "إضافة" if amount > 0 else "خصم"
        try:
            bot.send_message(int(target_id), f"تم {action_text} {abs(amount)}$ من رصيدك.\nملاحظة: {note}\nرصيدك الحالي: {data['balance'][target_id]}$")
        except:
            pass

        user_sessions.pop(uid)
        return bot.send_message(message.chat.id, f"تم {action_text} {abs(amount)}$ للمستخدم {target_id}\nالرصيد الحالي: {data['balance'][target_id]}$")

    if sess.get("step") == "add_balance_user":
        try:
            target_id = str(int(text))
            if target_id not in data["users"]:
                return bot.send_message(message.chat.id, "المستخدم غير موجود.")
            sess["target_id"] = target_id
            sess["step"] = "add_balance_amount"
            return bot.send_message(message.chat.id, "أرسل المبلغ المراد إضافته:")
        except:
            return bot.send_message(message.chat.id, "معرف غير صالح.")

    if sess.get("step") == "add_balance_amount":
        try:
            amount = float(text)
            target_id = sess["target_id"]
            update_balance(target_id, amount)
            user_sessions.pop(uid)
            return bot.send_message(message.chat.id, f"تم إضافة {amount}$ إلى المستخدم {target_id}\nالرصيد الحالي: {data['balance'][target_id]}$")
        except:
            return bot.send_message(message.chat.id, "مبلغ غير صالح.")

    # Remove all emojis from text for command matching
    clean_text = text
    for emoji in ["🛒 ", "💰 ", "🔐 ", "📞 ", "🌐 ", "🔒 ", "⚡ ", "🔙 "]:
        clean_text = clean_text.replace(emoji, "")

    if clean_text == "شراء بروكسي":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🌐 HTTP", "🔒 SOCKS5", "⚡ Inject", "🔙 رجوع")
        user_sessions[uid] = {"step": "type"}
        msg = "🎯 اختيار نوع البروكسي\n"
        msg+= "━━━━━━━━━━━━━━\n"
        msg += "📌 متطلبات كلمة المرور والمستخدم:\n\n"
        msg += "✦ 12 حرف على الأقل\n"
        msg += "✦ حرف كبير واحد على الأقل\n"
        msg += "✦ رقم واحد على الأقل\n"
        msg += "━━━━━━━━━━━━━━\n"
        msg += "🔽 اختر النوع المناسب:"
        return bot.send_message(message.chat.id, msg, reply_markup=markup)

    if sess.get("step") == "type":
        clean_type = text
        for emoji in ["🌐 ", "🔒 ", "⚡ "]:
            clean_type = clean_type.replace(emoji, "")
        type_map = {"HTTP": "http", "SOCKS5": "socks5", "Inject": "inject"}
        proxy_type = type_map.get(clean_type)
        if proxy_type:
            sess["type"] = proxy_type
            sess["step"] = "server_selection"
            # عرض قائمة الخوادم المتاحة
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for server_id, server_info in data["servers"].items():
                if server_info.get("active", True):
                    markup.add(server_info["name"])
            markup.add("رجوع")
            return bot.send_message(message.chat.id, "اختر الخادم:", reply_markup=markup)
            # إظهار الأسعار مباشرة للفترات القصيرة
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(
                f"3 ساعات: {data['prices']['3hours']}$",
                f"12 ساعة: {data['prices']['12hours']}$"
            )
            markup.add(
                f"يوم: {data['prices']['day']}$"
            )
            markup.add("أسبوع/شهر (خيارات متقدمة)")
            markup.add("رجوع")
            return bot.send_message(message.chat.id, "اختر المدة:", reply_markup=markup)
        return

    if sess.get("step") == "server_selection":
        # البحث عن الخادم المختار
        selected_server = None
        for server_id, server_info in data["servers"].items():
            if server_info["name"] == text and server_info.get("active", True):
                selected_server = server_id
                break

        if selected_server:
            sess["server_id"] = selected_server
            sess["step"] = "duration"
            # إظهار الأسعار مباشرة للفترات القصيرة
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(
                f"3 ساعات: {data['prices']['3hours']}$",
                f"12 ساعة: {data['prices']['12hours']}$"
            )
            markup.add(
                f"يوم: {data['prices']['day']}$"
            )
            markup.add("أسبوع/شهر (خيارات متقدمة)")
            markup.add("رجوع")
            return bot.send_message(message.chat.id, f"تم اختيار {text}\nاختر المدة:", reply_markup=markup)
        return

    if text == "أسبوع/شهر (خيارات متقدمة)" and sess.get("step") == "duration":
        sess["step"] = "proxy_options"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("بروكسي عادي", "بروكسي مع تغيير IP")
        markup.add("رجوع")
        return bot.send_message(message.chat.id, "اختر نوع البروكسي للفترات الطويلة:", reply_markup=markup)

    if sess.get("step") == "proxy_options":
        if text in ["بروكسي عادي", "بروكسي مع تغيير IP"]:
            sess["with_api"] = text == "بروكسي مع تغيير IP"
            if sess["type"] == "inject" and not sess["with_api"]:
                sess["with_whitelist"] = True
            else:
                sess["with_whitelist"] = False
            sess["step"] = "duration_advanced"
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

            # استخدام أسعار منفصلة للبروكسيات مع تغيير IP
            if sess.get("with_api"):
                markup.add(
                    f"أسبوع: {data['prices']['week_api']}$",
                    f"شهر: {data['prices']['month_api']}$"
                )
            else:
                markup.add(
                    f"أسبوع: {data['prices']['week']}$",
                    f"شهر: {data['prices']['month']}$"
                )
            markup.add("رجوع")
            return bot.send_message(message.chat.id, "اختر المدة:", reply_markup=markup)

    # معالجة اختيار المدة للفترات القصيرة (بدون تغيير IP)
    if sess.get("step") == "duration" and ":" in text and text != "أسبوع/شهر (خيارات متقدمة)":
        try:
            label, price_text = text.split(":")
            duration_map = {"3 ساعات": "3hours", "12 ساعة": "12hours", "يوم": "day"}
            key = duration_map.get(label.strip())
            if not key:
                return bot.send_message(message.chat.id, "خيار غير صالح.")
            hours_map = {"3hours": 3, "12hours": 12, "day": 24}
            minutes = hours_map[key] * 60
            cost = float(price_text.replace("$", "").strip())
            if data["balance"].get(uid, 0) < cost:
                return bot.send_message(message.chat.id, "الرصيد غير كافٍ.")
            sess.update({"duration": minutes, "cost": cost, "with_api": False})
            if sess["type"] == "inject":
                sess["step"] = "ip"
                return bot.send_message(message.chat.id, "أرسل عنوان الـIP:")
            else:
                sess["step"] = "password"
                sess["username"] = "WorkTrekProxy5G"  # اسم المستخدم الافتراضي
                return bot.send_message(message.chat.id, "أدخل كلمة المرور:")
        except:
            return bot.send_message(message.chat.id, "خيار غير صالح.")

    # معالجة اختيار المدة للفترات الطويلة (مع أو بدون تغيير IP)
    if sess.get("step") == "duration_advanced" and ":" in text:
        try:
            label, price_text = text.split(":")
            duration_map = {"أسبوع": "week", "شهر": "month"}
            key = duration_map.get(label.strip())
            if not key:
                return bot.send_message(message.chat.id, "خيار غير صالح.")
            hours_map = {"week": 168, "month": 720}
            minutes = hours_map[key] * 60
            cost = float(price_text.replace("$", "").strip())
            if data["balance"].get(uid, 0) < cost:
                return bot.send_message(message.chat.id, "الرصيد غير كافٍ.")
            sess.update({"duration": minutes, "cost": cost})
            if sess["type"] == "inject":
                sess["step"] = "ip"
                return bot.send_message(message.chat.id, "أرسل عنوان الـIP:")
            else:
                sess["step"] = "password"
                sess["username"] = "WorkTrekProxy5G"  # اسم المستخدم الافتراضي
                return bot.send_message(message.chat.id, "أدخل كلمة المرور:")
        except:
            return bot.send_message(message.chat.id, "خيار غير صالح.")

    if sess.get("step") == "ip":
        ip = text.strip()
        server_id = sess.get("server_id", "usa1")
        result = create_proxy(data["api_key"], "inject", sess["duration"], ip=ip, with_api=True, server_id=server_id)
        if "error" in result:
            return bot.send_message(message.chat.id, "خطأ: " + result["error"])
        result['with_api'] = sess.get('with_api', False)  # حفظ معلومات تغيير IP
        data.setdefault("proxies", {}).setdefault(uid, []).append(result)
        update_balance(uid, -sess["cost"])
        user_sessions.pop(uid)
        msg = "⚠️ تحذيرات هامة:\n"
        msg += "━━━━━━━━━━━━━━\n"
        msg += "❌ يمنع مشاركة البروكسي لأكثر من شخص\n"
        msg += "❌ يمنع بيع البروكسي - البروكسي مخصص لك فقط\n"
        msg += "❌ يمنع الاستهلاك العالي جداً\n"
        msg += "⚠️ مخالفة الشروط تؤدي إلى إلغاء خدمتك تلقائياً\n"
        msg += "━━━━━━━━━━━━━━\n\n"
        msg += "✅ تم إنشاء بروكسي Inject بنجاح!\n\n"
        msg += "🔐 معلومات البروكسي:\n"
        msg += "━━━━━━━━━━━━━━\n"
        msg += f"🖥️ الخادم: {result.get('server_name', 'غير محدد')}\n"
        msg += f"🌐 IP: `{result['ip']}`\n"
        msg += f"🔌 Port: `{result['port']}`\n"
        msg += "━━━━━━━━━━━━━━\n"
        msg += f"⏰ ينتهي في: {result['date_end']}\n"
        msg += f"💰 رصيدك المتبقي: {data['balance'][uid]}$"
        return bot.send_message(message.chat.id, msg, parse_mode="Markdown")

    if sess.get("step") == "password":
        username = "WorkTrekProxy5G"
        password = text.strip()
        if username == password:
            return bot.send_message(message.chat.id, "⚠️ يجب أن تكون كلمة المرور مختلفة عن اسم المستخدم")
        #if not (is_valid(username) and is_valid(password)):
        #    return bot.send_message(message.chat.id, "كلمة المرور أو اسم المستخدم غير صالح.")
        server_id = sess.get("server_id", "usa1")
        result = create_proxy(data["api_key"], sess["type"], sess["duration"], username=username, password=password, with_api=sess.get("with_api", False), server_id=server_id)
        if "error" in result:
            return bot.send_message(message.chat.id, "خطأ: " + result["error"])
        result['with_api'] = sess.get('with_api', False)  # حفظ معلومات تغيير IP
        data.setdefault("proxies", {}).setdefault(uid, []).append(result)
        update_balance(uid, -sess["cost"])
        user_sessions.pop(uid)
        msg = "⚠️ تحذيرات هامة:\n"
        msg += "━━━━━━━━━━━━━━\n"
        msg += "❌ يمنع مشاركة البروكسي لأكثر من شخص\n"
        msg += "❌ يمنع بيع البروكسي - البروكسي مخصص لك فقط\n"
        msg += "❌ يمنع الاستهلاك العالي جداً\n"
        msg += "⚠️ مخالفة الشروط تؤدي إلى إلغاء خدمتك تلقائياً\n"
        msg += "━━━━━━━━━━━━━━\n\n"
        msg += "✅ تم إنشاء البروكسي بنجاح!\n\n"
        msg += "🔐 معلومات البروكسي:\n"
        msg += "━━━━━━━━━━━━━━\n"
        msg += f"🖥️ الخادم: {result.get('server_name', 'غير محدد')}\n"
        msg += f"🌐 IP: `{result['ip']}`\n"
        msg += f"🔌 Port: `{result['port']}`\n"
        msg += f"👤 Username: `{username}`\n"
        msg += f"🔑 Password: `{password}`\n"
        msg += "━━━━━━━━━━━━━━\n"
        msg += f"⏰ ينتهي في: {result['date_end']}\n"
        msg += f"💰 رصيدك المتبقي: {data['balance'][uid]}$"
        return bot.send_message(message.chat.id, msg, parse_mode="Markdown")

    if text == "تغيير عنوان IP الحقيقي":
        try:
            update_url = "https://i.fxdx.in/api-rt/changeip/M3BnghwHrk/xKN6MKNMXCNBP"
            response = requests.get(update_url, timeout=10)
            if response.status_code == 200:
                # تأكيد تغيير IP
                ip_response = requests.get("https://api.ipify.org?format=json", timeout=10)
                if ip_response.status_code == 200:
                    new_ip = ip_response.json()["ip"]
                    return bot.send_message(message.chat.id, f"✅ تم تغيير عنوان IP الحقيقي بنجاح\nIP الجديد: {new_ip}")
        except Exception as e:
            print(f"Error updating real IP: {e}")
            return bot.send_message(message.chat.id, "❌ حدث خطأ أثناء تغيير عنوان IP الحقيقي")

    if sess.get("step") == "select_proxy_for_ip_update" and " - " in text:
        try:
            port = int(text.split(" ")[1])
            proxies = data.get("proxies", {}).get(uid, [])
            selected_proxy = next((p for p in proxies if p["port"] == port), None)

            if not selected_proxy:
                return bot.send_message(message.chat.id, "البروكسي غير موجود.")

            user_sessions[uid] = {
                "step": "update_ip",
                "proxy_id": selected_proxy["proxy_id"],
                "port": port
            }
            return bot.send_message(message.chat.id, "أرسل الـ IP الجديد:")
        except:
            return bot.send_message(message.chat.id, "خطأ في اختيار البروكسي.")

    if sess.get("step") == "update_ip":
        proxy_id = sess.get("proxy_id")
        port = sess.get("port")

        try:
            selected_proxy = next((p for p in data["proxies"][uid] if p["proxy_id"] == proxy_id), None)
            if not selected_proxy:
                return bot.send_message(message.chat.id, "لم يتم العثور على البروكسي.")

            if selected_proxy["type"] == "inject":
                server_id = selected_proxy.get("server_id", "usa1")
                result = update_proxy_ip(proxy_id, text.strip(), server_id)

                if result.get("success"):
                    for proxy in data["proxies"][uid]:
                        if proxy["proxy_id"] == proxy_id:
                            proxy["allow_from"] = [text.strip()]
                    save_data(data)
                    user_sessions.pop(uid)
                    return bot.send_message(message.chat.id, f"✅ تم تحديث IP Whitelist للبروكسي بنجاح.")
                else:
                    return bot.send_message(message.chat.id, f"❌ {result.get('error', 'فشل تحديث IP')}")
            elif selected_proxy.get("login"):  # للبروكسيات مع يوزر وباسوورد
                try:
                    update_url = f"https://i.fxdx.in/api-rt/changeip/{proxy_id}/xKN6MKNMXCNBP"
                    response = requests.get(update_url, timeout=10)
                    if response.status_code == 200:
                        # تأكيد تغيير IP
                        ip_response = requests.get("https://api.ipify.org?format=json", timeout=10)
                        if ip_response.status_code == 200:
                            new_ip = ip_response.json()["ip"]
                            for proxy in data["proxies"][uid]:
                                if proxy["proxy_id"] == proxy_id:
                                    proxy["ip"] = new_ip
                            save_data(data)
                            return bot.send_message(message.chat.id, f"✅ تم تحديث IP البروكسي بنجاح\nIP الجديد: {new_ip}")
                except Exception as e:
                    print(f"Error updating proxy IP: {e}")
                    return bot.send_message(message.chat.id, "❌ حدث خطأ أثناء تحديث IP البروكسي")
            else:  # للبروكسيات بدون يوزر وباسوورد
                return bot.send_message(message.chat.id, "هذا النوع من البروكسي لا يدعم تغيير IP")
            if response.status_code == 200:
                proxies = data.get("proxies", {}).get(uid, [])
                for proxy in proxies:
                    if proxy["port"] == port:
                        proxy["ip"] = ip
                        break
                save_data(data)
                user_sessions.pop(uid)
                return bot.send_message(message.chat.id, f"✅ تم تحديث IP البروكسي {port} بنجاح.")
            else:
                return bot.send_message(message.chat.id, f"❌ فشل تحديث IP: {response.status_code}")
        except Exception as e:
            return bot.send_message(message.chat.id, f"❌ حدث خطأ: {str(e)}")

        for proxy in api_proxies:
            try:
                proxy_id = proxy.get("proxy_id")
                if not proxy_id:
                    continue

                update_url = f"https://iproxy.online/api/cn/v1/proxy-access/{proxy_id}/update"
                headers = {
                    "Authorization": f"Bearer {data['api_key']}",
                    "Content-Type": "application/merge-patch+json"
                }
                payload = {
                    "auth_type": "noauth",
                    "allow_from": [ip]
                }

                response = requests.post(update_url, headers=headers, json=payload, timeout=10)
                if response.status_code == 200:
                    proxy["ip"] = ip
                    success_count += 1
                else:
                    failed_proxies.append(proxy_id)

            except Exception as e:
                failed_proxies.append(proxy_id)
                print(f"خطأ في تحديث IP للبروكسي {proxy_id}: {str(e)}")

        save_data(data)
        user_sessions.pop(uid)

        if success_count == len(api_proxies):
            return bot.send_message(message.chat.id, "✅ تم تحديث IP لجميع البروكسيات بنجاح.")
        elif success_count > 0:
            msg = f"⚠️ تم تحديث {success_count} من {len(api_proxies)} بروكسي."
            if failed_proxies:
                msg += "\nفشل تحديث البروكسيات التالية:\n" + "\n".join(failed_proxies)
            return bot.send_message(message.chat.id, msg)
        else:
            return bot.send_message(message.chat.id, "❌ فشل تحديث جميع البروكسيات.")

    if sess.get("step") == "select_user_delete_proxy" and " - " in text:
        try:
            target_id = text.split(" - ")[1]
            proxies = data.get("proxies", {}).get(target_id, [])
            if not proxies:
                return bot.send_message(message.chat.id, "لا يوجد بروكسيات لهذا المستخدم.")

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for proxy in proxies:
                proxy_info = f"{proxy['type'].upper()} - {proxy.get('proxy_id', 'N/A')} ({proxy['ip']}:{proxy['port']})"
                markup.add(proxy_info)
            markup.add("حذف جميع البروكسيات")
            markup.add("رجوع")

            sess["target_id"] = target_id
            sess["step"] = "delete_user_proxy"
            return bot.send_message(message.chat.id, "اختر البروكسي للحذف:", reply_markup=markup)
        except:
            return bot.send_message(message.chat.id, "خطأ في اختيار المستخدم.")

    if sess.get("step") == "delete_user_proxy":
        target_id = sess["target_id"]
        if text == "حذف جميع البروكسيات":
            proxies = data.get("proxies", {}).get(target_id, [])
            for proxy in proxies:
                try:
                    proxy_id = proxy.get("proxy_id")
                    if proxy_id:
                        # الحصول على API key المناسب للخادم
                        server_id = proxy.get("server_id", "usa1")
                        server_info = data["servers"].get(server_id, {})
                        api_key = server_info.get("api_key", data["api_key"])

                        requests.delete(
                            f"https://iproxy.online/api/cn/v1/proxy-access/{proxy_id}",
                            headers={"Authorization": f"Bearer {api_key}"}
                        )
                except:
                    continue
            data["proxies"][target_id] = []
            save_data(data)
            user_sessions.pop(uid)
            return bot.send_message(message.chat.id, "تم حذف جميع البروكسيات للمستخدم.")

        elif "(" in text and ")" in text:
            try:
                proxy_id = text.split(" - ")[1].split(" (")[0]
                proxies = data.get("proxies", {}).get(target_id, [])
                proxy_found = False

                for proxy in proxies:
                    if str(proxy.get("proxy_id")) == proxy_id:
                        proxy_found = True
                        try:
                            # الحصول على API key المناسب للخادم
                            server_id = proxy.get("server_id", "usa1")
                            server_info = data["servers"].get(server_id, {})
                            api_key = server_info.get("api_key", data["api_key"])

                            response = requests.delete(
                                f"https://iproxy.online/api/cn/v1/proxy-access/{proxy_id}",
                                headers={"Authorization": f"Bearer {api_key}"}
                            )
                            if response.status_code == 200:
                                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                                markup.add("نعم", "لا")
                                markup.add("رجوع")
                                user_sessions[uid].update({
                                    "step": "delete_proxy_note",
                                    "proxy_id": proxy_id,
                                    "target_id": target_id,
                                    "proxies_backup": proxies
                                })
                                return bot.send_message(message.chat.id, "هل تريد إرسال ملاحظة للمستخدم؟", reply_markup=markup)
                            else:
                                return bot.send_message(message.chat.id, f"فشل في حذف البروكسي. كود الخطأ: {response.status_code}")
                        except Exception as e:
                            print(f"Error deleting proxy: {e}")
                            return bot.send_message(message.chat.id, "حدث خطأ أثناء محاولة حذف البروكسي.")

                if not proxy_found:
                    return bot.send_message(message.chat.id, "لم يتم العثور على البروكسي المحدد.")
            except Exception as e:
                print(f"Error processing delete request: {e}")
                return bot.send_message(message.chat.id, "حدث خطأ في معالجة طلب الحذف.")

    if text == "حذف البروكسيات":
        proxies = data.get("proxies", {}).get(uid, [])
        if not proxies:
            return bot.send_message(message.chat.id, "لا يوجد بروكسيات لديك.")

        for proxy in proxies:
            try:
                proxy_id = proxy.get("proxy_id") or proxy.get("id")
                if proxy_id:
                    # الحصول على API key المناسب للخادم
                    server_id = proxy.get("server_id", "usa1")
                    server_info = data["servers"].get(server_id, {})
                    api_key = server_info.get("api_key", data["api_key"])

                    requests.delete(
                        f"https://iproxy.online/api/cn/v1/proxy-access/{proxy_id}",
                        headers={"Authorization": f"Bearer {api_key}"}
                    )
            except:
                continue

        data["proxies"][uid] = []
        save_data(data)
        return bot.send_message(message.chat.id, "تم حذف جميع البروكسيات الخاصة بك.")

    # Handle the "انشاء الرابط" option
    if text == "إضافة رابط جديد لتغيير IP" and uid == str(ADMIN_ID):
        user_sessions[uid] = {"step": "add_ip_url"}
        return bot.send_message(message.chat.id, "أرسل الرابط الجديد لتغيير IP:")

    if sess.get("step") == "add_ip_url" and uid == str(ADMIN_ID):
        if not text.startswith(("http://", "https://")):
            return bot.send_message(message.chat.id, "❌ يجب أن يبدأ الرابط بـ http:// أو https://")
        try:
            # حفظ الرابط مباشرة
            data["ip_change_url"] = text
            save_data(data)
            user_sessions.pop(uid)
            return bot.send_message(message.chat.id, "✅ تم إضافة/تحديث الرابط بنجاح")
        except Exception as e:
            print(f"Error updating URL: {e}")
            return bot.send_message(message.chat.id, "❌ حدث خطأ في حفظ الرابط")
    if (clean_text == "تحديث API" or text == "🔄 تحديث API") and uid == str(ADMIN_ID):
        user_sessions[uid] = {"step": "update_api"}
        return bot.send_message(message.chat.id, "أرسل مفتاح API الجديد:")

    if sess.get("step") == "update_api" and uid == str(ADMIN_ID):
        new_api_key = text.strip()
        if len(new_api_key) != 64:
            return bot.send_message(call.message.chat.id, "❌ مفتاح API يجب أن يكون 64 رمز.")
        data["api_key"] = new_api_key
        save_data(data)
        user_sessions.pop(uid)
        return bot.send_message(call.message.chat.id, "✅ تم تحديث مفتاح API بنجاح")

    if text == "تعديل أسعار الصرف" and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("تعديل سعر الليرة السورية", "تعديل سعر الجنيه المصري")
        markup.add("رجوع")
        return bot.send_message(message.chat.id, "اختر العملة المراد تعديل سعر صرفها:", reply_markup=markup)

    if text in ["تعديل سعر الليرة السورية", "تعديل سعر الجنيه المصري"]:
        currency = "syrian_pound" if text == "تعديل سعر الليرة السورية" else "egyptian_pound"
        user_sessions[uid] = {"step": "update_exchange_rate", "currency": currency}
        return bot.send_message(message.chat.id, f"أدخل السعر الجديد للدولار مقابل {text.replace('تعديل سعر ', '')}:")

    if sess.get("step") == "edit_deposit_amount":
        try:
            new_amount = float(text)
            deposit_id = sess["deposit_id"]
            deposit = data["pending_deposits"].get(deposit_id)

            if deposit and deposit["status"] == "pending":
                old_amount = deposit["amount"]
                deposit["amount"] = new_amount
                deposit["amount_edited"] = True
                deposit["old_amount"] = old_amount
                save_data(data)

                sess["step"] = "edit_deposit_note"
                return bot.send_message(message.chat.id, "أدخل ملاحظة حول سبب تعديل المبلغ:")
            else:
                user_sessions.pop(uid)
                return bot.send_message(message.chat.id, "الطلب غير موجود أو تم معالجته مسبقاً")
        except:
            return bot.send_message(message.chat.id, "الرجاء إدخال مبلغ صحيح")

    if sess.get("step") == "edit_deposit_note":
        deposit_id = sess["deposit_id"]
        deposit = data["pending_deposits"].get(deposit_id)

        if deposit and deposit["status"] == "pending":
            deposit["edit_note"] = text
            save_data(data)

            try:
                user_msg = f"⚠️ تم تعديل مبلغ طلب الإيداع الخاص بك\n"
                user_msg += "━━━━━━━━━━━━━━\n"
                user_msg += f"💰 المبلغ القديم: {deposit['old_amount']}$\n"
                user_msg += f"💰 المبلغ الجديد: {deposit['amount']}$\n"
                user_msg += f"📝 ملاحظة: {text}\n"
                user_msg += f"🧾 رقم الطلب: {deposit_id}"

                bot.send_message(deposit["user_id"], user_msg)
            except:
                pass

            user_sessions.pop(uid)
            return bot.send_message(message.chat.id, "✅ تم تعديل المبلغ وإرسال الإشعار للمستخدم")

    if text == "💰 تحكم بنظام الإيداع" and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📋 طلبات الإيداع المعلقة")
        markup.add("⚙️ إدارة طرق الدفع")
        markup.add("💱 تعديل أسعار الصرف")
        markup.add("رجوع")
        return bot.send_message(message.chat.id, "اختر من القائمة:", reply_markup=markup)

    if text == "📋 طلبات الإيداع المعلقة" and uid == str(ADMIN_ID):
        pending = data.get("pending_deposits", {})
        pending_count = sum(1 for d in pending.values() if d.get("status") == "pending")

        if pending_count == 0:
            return bot.send_message(message.chat.id, "لا توجد طلبات إيداع معلقة")

        markup = types.InlineKeyboardMarkup(row_width=1)
        for deposit_id, deposit in pending.items():
            if deposit.get("status") == "pending":
                try:
                    user = bot.get_chat(int(deposit["user_id"]))
                    user_name = user.first_name if user else "غير معروف"
                    username = f"@{user.username}" if user and user.username else "لا يوجد معرف"

                    button_text = f"💰 {deposit['amount']}$ - {user_name}"
                    markup.add(types.InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"view_deposit:{deposit_id}"
                    ))
                except Exception as e:
                    print(f"Error processing deposit {deposit_id}: {e}")
                    continue

        msg = "📋 طلبات الإيداع المعلقة\n"
        msg += "اضغط على الطلب للموافقة أو الرفض"
        return bot.send_message(message.chat.id, msg, reply_markup=markup)

    if text == "⚙️ إدارة طرق الدفع" and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for method_id, method in data["payment_methods"].items():
            status = "✅" if method["active"] else "❌"
            markup.add(f"{status} {method['name']}")
        markup.add("رجوع")
        return bot.send_message(message.chat.id, "اختر طريقة الدفع لإدارتها:", reply_markup=markup)

    if text.startswith(("✅ ", "❌ ")) and uid == str(ADMIN_ID):
        method_name = text[2:]
        for method_id, method in data["payment_methods"].items():
            if method["name"] == method_name:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add("تغيير الحالة", "تعديل العنوان")
                markup.add("تعديل الحد الأدنى", "تعديل الحد الأقصى")
                markup.add("رجوع")

                if uid not in user_sessions:
                    user_sessions[uid] = {}
                user_sessions[uid]["edit_payment_method"] = method_id

                msg = f"⚙️ إدارة {method_name}\n"
                msg += "━━━━━━━━━━━━━━\n"
                msg += f"الحالة: {'مفعل' if method['active'] else 'معطل'}\n"
                msg += f"العنوان: {method['address']}\n"
                msg += f"الحد الأدنى: {method['min_amount']}$\n"
                msg += f"الحد الأقصى: {method['max_amount']}$\n"

                return bot.send_message(message.chat.id, msg, reply_markup=markup)

    if text == "تغيير الحالة" and uid == str(ADMIN_ID):
        method_id = sess.get("edit_payment_method")
        if not method_id:
            return

        data["payment_methods"][method_id]["active"] = not data["payment_methods"][method_id]["active"]
        save_data(data)

        status = "تفعيل" if data["payment_methods"][method_id]["active"] else "تعطيل"
        return bot.send_message(message.chat.id, f"تم {status} طريقة الدفع بنجاح")

    if text == "تعديل العنوان" and uid == str(ADMIN_ID):
        method_id = sess.get("edit_payment_method")
        if not method_id:
            return

        sess["edit_step"] = "address"
        return bot.send_message(message.chat.id, "أدخل العنوان الجديد:")

    if text == "تعديل الحد الأدنى" and uid == str(ADMIN_ID):
        method_id = sess.get("edit_payment_method")
        if not method_id:
            return

        sess["edit_step"] = "min_amount"
        return bot.send_message(message.chat.id, "أدخل الحد الأدنى الجديد:")

    if text == "تعديل الحد الأقصى" and uid == str(ADMIN_ID):
        method_id = sess.get("edit_payment_method")
        if not method_id:
            return

        sess["edit_step"] = "max_amount"
        return bot.send_message(message.chat.id, "أدخل الحد الأقصى الجديد:")

    if sess.get("edit_step") in ["min_amount", "max_amount"]:
        method_id = sess.get("edit_payment_method")
        if not method_id:
            return

        try:
            amount = float(text)
            if amount <= 0:
                return bot.send_message(message.chat.id, "يجب أن يكون المبلغ أكبر من صفر")

            if sess["edit_step"] == "min_amount":
                data["payment_methods"][method_id]["min_amount"] = amount
            else:
                data["payment_methods"][method_id]["max_amount"] = amount

            save_data(data)
            user_sessions.pop(uid, None)
            return bot.send_message(message.chat.id, "✅ تم تحديث الحد بنجاح")
        except:
            return bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح")

    if sess.get("edit_step") == "address":
        method_id = sess.get("edit_payment_method")
        if not method_id:
            return

        data["payment_methods"][method_id]["address"] = text.strip()
        save_data(data)
        user_sessions.pop(uid, None)
        return bot.send_message(message.chat.id, "✅ تم تحديث العنوان بنجاح")

    if (clean_text == "تعديل أسعار الصرف" or text == "💱 تعديل أسعار الصرف") and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("تعديل سعر الليرة السورية", "تعديل سعر الجنيه المصري")
        markup.add("رجوع")
        return bot.send_message(message.chat.id, "اختر العملة المراد تعديل سعر صرفها:", reply_markup=markup)

    if text in ["تعديل سعر الليرة السورية", "تعديل سعر الجنيه المصري"]:
        currency = "syrian_pound" if text == "تعديل سعر الليرة السورية" else "egyptian_pound"
        user_sessions[uid] = {"step": "update_exchange_rate", "currency": currency}
        return bot.send_message(message.chat.id, f"أدخل السعر الجديد للدولار مقابل {text.replace('تعديل سعر ', '')}:")

    if sess.get("step") == "update_exchange_rate":
        try:
            exchange_rate = float(text)
            currency = sess["currency"]
            if "exchange_rates" not in data:
                data["exchange_rates"] = {}

            data["exchange_rates"][currency] = exchange_rate
            save_data(data)
            user_sessions.pop(uid)
            return bot.send_message(message.chat.id, f"تم تحديث سعر الصرف بنجاح إلى {exchange_rate}")
        except:
            return bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح")

    # معالجة عمليات إدارة الخوادم
    if text == "⚙️ إدارة الخوادم" and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📋 عرض الخوادم", "➕ إضافة خادم")
        markup.add("✏️ تعديل خادم", "🗑️ حذف خادم")
        markup.add("🔄 تفعيل/إلغاء خادم", "🔗 إدارة روابط IP")
        markup.add("🔧 إيقاف سيرفر بسبب عطل")
        markup.add("رجوع")
        return bot.send_message(message.chat.id, "اختر عملية إدارة الخوادم:", reply_markup=markup)

    if text == "📋 عرض الخوادم" and uid == str(ADMIN_ID):
        if not data.get("servers"):
            return bot.send_message(message.chat.id, "لا توجد خوادم مسجلة")

        msg = "🖥️ قائمة الخوادم:\n"
        msg += "━━━━━━━━━━━━━━\n"
        for server_id, server_info in data["servers"].items():
            status = "🟢 مفعل" if server_info.get("active", True) else "🔴 معطل"
            ip_url_status = "🔗 متوفر" if server_info.get("ip_change_url") else "❌ غير متوفر"
            msg += f"🔹 {server_info['name']}\n"
            msg += f"   المعرف: {server_id}\n"
            msg += f"   الحالة: {status}\n"
            msg += f"   Endpoint: {server_info['endpoint']}\n"
            msg += f"   رابط تغيير IP: {ip_url_status}\n"
            if server_info.get("api_key"):
                msg += f"   API Key: مخصص\n"
            else:
                msg += f"   API Key: افتراضي\n"
            msg += "───────────────\n"
        return bot.send_message(message.chat.id, msg)

    if text == "➕ إضافة خادم" and uid == str(ADMIN_ID):
        user_sessions[uid] = {"step": "add_server_id"}
        return bot.send_message(message.chat.id, "أدخل معرف الخادم الجديد (مثل: usa3, europe2):")

    if text == "✏️ تعديل خادم" and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for server_id, server_info in data["servers"].items():
            markup.add(f"{server_info['name']} ({server_id})")
        markup.add("رجوع")
        user_sessions[uid] = {"step": "select_server_edit"}
        return bot.send_message(message.chat.id, "اختر الخادم للتعديل:", reply_markup=markup)

    if text == "🗑️ حذف خادم" and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for server_id, server_info in data["servers"].items():
            markup.add(f"{server_info['name']} ({server_id})")
        markup.add("رجوع")
        user_sessions[uid] = {"step": "select_server_delete"}
        return bot.send_message(message.chat.id, "اختر الخادم للحذف:", reply_markup=markup)

    if text == "🔄 تفعيل/إلغاء خادم" and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for server_id, server_info in data["servers"].items():
            status = "🟢" if server_info.get("active", True) else "🔴"
            markup.add(f"{status} {server_info['name']} ({server_id})")
        markup.add("رجوع")
        user_sessions[uid] = {"step": "toggle_server_status"}
        return bot.send_message(message.chat.id, "اختر الخادم لتغيير حالته:", reply_markup=markup)

    if text == "🔗 إدارة روابط IP" and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📋 عرض روابط IP", "➕ إضافة/تعديل رابط IP")
        markup.add("🗑️ حذف رابط IP", "رجوع")
        return bot.send_message(message.chat.id, "اختر عملية إدارة روابط تغيير IP:", reply_markup=markup)

    if text == "🔧 إيقاف سيرفر بسبب عطل" and uid == str(ADMIN_ID):
        # عرض الخوادم التي تحتوي على بروكسيات نشطة
        servers_with_proxies = {}
        for user_id, user_proxies in data.get("proxies", {}).items():
            for proxy in user_proxies:
                server_id = proxy.get("server_id", "usa1")
                if server_id not in servers_with_proxies:
                    servers_with_proxies[server_id] = 0
                servers_with_proxies[server_id] += 1

        if not servers_with_proxies:
            return bot.send_message(message.chat.id, "لا توجد خوادم تحتوي على بروكسيات نشطة")

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for server_id, proxy_count in servers_with_proxies.items():
            server_info = data["servers"].get(server_id, {})
            server_name = server_info.get("name", server_id)
            markup.add(f"🔧 {server_name} ({proxy_count} بروكسي)")
        markup.add("رجوع")
        
        user_sessions[uid] = {"step": "select_server_maintenance"}
        return bot.send_message(message.chat.id, "اختر السيرفر المراد إيقافه بسبب عطل:", reply_markup=markup)

    if text == "📋 عرض روابط IP" and uid == str(ADMIN_ID):
        if not data.get("servers"):
            return bot.send_message(message.chat.id, "لا توجد خوادم مسجلة")

        msg = "🔗 روابط تغيير IP للخوادم:\n"
        msg += "━━━━━━━━━━━━━━\n"
        for server_id, server_info in data["servers"].items():
            msg += f"🔹 {server_info['name']} ({server_id})\n"
            if server_info.get("ip_change_url"):
                msg += f"   🔗 الرابط: {server_info['ip_change_url']}\n"
            else:
                msg += f"   ❌ لا يوجد رابط\n"
            msg += "───────────────\n"
        return bot.send_message(message.chat.id, msg)

    if text == "➕ إضافة/تعديل رابط IP" and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for server_id, server_info in data["servers"].items():
            status = "🔗" if server_info.get("ip_change_url") else "➕"
            markup.add(f"{status} {server_info['name']} ({server_id})")
        markup.add("رجوع")
        user_sessions[uid] = {"step": "select_server_ip_url"}
        return bot.send_message(message.chat.id, "اختر الخادم لإضافة/تعديل رابط تغيير IP:", reply_markup=markup)

    if text == "🗑️ حذف رابط IP" and uid == str(ADMIN_ID):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        has_urls = False
        for server_id, server_info in data["servers"].items():
            if server_info.get("ip_change_url"):
                markup.add(f"🔗 {server_info['name']} ({server_id})")
                has_urls = True
        if not has_urls:
            return bot.send_message(message.chat.id, "لا توجد خوادم تحتوي على روابط تغيير IP")
        markup.add("رجوع")
        user_sessions[uid] = {"step": "delete_server_ip_url"}
        return bot.send_message(message.chat.id, "اختر الخادم لحذف رابط تغيير IP:", reply_markup=markup)

    # معالجة خطوات إضافة خادم جديد
    if sess.get("step") == "add_server_id":
        server_id = text.strip().lower()
        if server_id in data["servers"]:
            return bot.send_message(message.chat.id, "❌ معرف الخادم موجود مسبقاً. اختر معرف آخر:")

        sess["new_server_id"] = server_id
        sess["step"] = "add_server_name"
        return bot.send_message(message.chat.id, "أدخل اسم الخادم (مثل: 🇺🇸 أمريكا 3):")

    if sess.get("step") == "add_server_name":
        sess["new_server_name"] = text.strip()
        sess["step"] = "add_server_endpoint"
        return bot.send_message(message.chat.id, "أدخل endpoint للخادم:")

    if sess.get("step") == "add_server_endpoint":
        sess["new_server_endpoint"] = text.strip()
        sess["step"] = "add_server_api_choice"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("استخدام API key افتراضي", "إضافة API key مخصص")
        markup.add("رجوع")
        return bot.send_message(message.chat.id, "اختر نوع API key:", reply_markup=markup)

    if sess.get("step") == "add_server_api_choice":
        if text == "استخدام API key افتراضي":
            sess["step"] = "add_server_ip_url_choice"
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("إضافة رابط تغيير IP", "تخطي")
            markup.add("رجوع")
            return bot.send_message(message.chat.id, "هل تريد إضافة رابط تغيير IP لهذا الخادم؟", reply_markup=markup)

        elif text == "إضافة API key مخصص":
            sess["step"] = "add_server_api_key"
            return bot.send_message(message.chat.id, "أدخل API key المخصص للخادم:")

    if sess.get("step") == "add_server_ip_url_choice":
        if text == "إضافة رابط تغيير IP":
            sess["step"] = "add_server_ip_url_new"
            return bot.send_message(message.chat.id, "أدخل رابط تغيير IP للخادم:")
        elif text == "تخطي":
            # إنشاء الخادم بدون رابط IP
            server_id = sess["new_server_id"]
            data["servers"][server_id] = {
                "name": sess["new_server_name"],
                "endpoint": sess["new_server_endpoint"],
                "active": True
            }
            save_data(data)
            user_sessions.pop(uid)
            return bot.send_message(message.chat.id, f"✅ تم إضافة الخادم '{sess['new_server_name']}' بنجاح!")

    if sess.get("step") == "add_server_ip_url_new":
        ip_url = text.strip()
        if not ip_url.startswith(("http://", "https://")):
            return bot.send_message(message.chat.id, "❌ يجب أن يبدأ الرابط بـ http:// أو https://")

        # إنشاء الخادم مع رابط IP
        server_id = sess["new_server_id"]
        data["servers"][server_id] = {
            "name": sess["new_server_name"],
            "endpoint": sess["new_server_endpoint"],
            "ip_change_url": ip_url,
            "active": True
        }
        save_data(data)
        user_sessions.pop(uid)
        return bot.send_message(message.chat.id, f"✅ تم إضافة الخادم '{sess['new_server_name']}' مع رابط تغيير IP بنجاح!")

    if sess.get("step") == "add_server_api_key":
        api_key = text.strip()
        if len(api_key) != 64:
            return bot.send_message(message.chat.id, "❌ API key يجب أن يكون 64 رمز. حاول مرة أخرى:")

        sess["new_server_api_key"] = api_key
        sess["step"] = "add_server_ip_url_choice_with_api"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("إضافة رابط تغيير IP", "تخطي")
        markup.add("رجوع")
        return bot.send_message(message.chat.id, "هل تريد إضافة رابط تغيير IP لهذا الخادم؟", reply_markup=markup)

    if sess.get("step") == "add_server_ip_url_choice_with_api":
        if text == "إضافة رابط تغيير IP":
            sess["step"] = "add_server_ip_url_with_api"
            return bot.send_message(message.chat.id, "أدخل رابط تغيير IP للخادم:")
        elif text == "تخطي":
            # إنشاء الخادم مع API key مخصص بدون رابط IP
            server_id = sess["new_server_id"]
            data["servers"][server_id] = {
                "name": sess["new_server_name"],
                "endpoint": sess["new_server_endpoint"],
                "api_key": sess["new_server_api_key"],
                "active": True
            }
            save_data(data)
            user_sessions.pop(uid)
            return bot.send_message(message.chat.id, f"✅ تم إضافة الخادم '{sess['new_server_name']}' مع API key مخصص بنجاح!")

    if sess.get("step") == "add_server_ip_url_with_api":
        ip_url = text.strip()
        if not ip_url.startswith(("http://", "https://")):
            return bot.send_message(message.chat.id, "❌ يجب أن يبدأ الرابط بـ http:// أو https://")

        # إنشاء الخادم مع API key مخصص ورابط IP
        server_id = sess["new_server_id"]
        data["servers"][server_id] = {
            "name": sess["new_server_name"],
            "endpoint": sess["new_server_endpoint"],
            "api_key": sess["new_server_api_key"],
            "ip_change_url": ip_url,
            "active": True
        }
        save_data(data)
        user_sessions.pop(uid)
        return bot.send_message(message.chat.id, f"✅ تم إضافة الخادم '{sess['new_server_name']}' مع API key ورابط تغيير IP بنجاح!")

    # معالجة تعديل الخوادم
    if sess.get("step") == "select_server_edit" and "(" in text and ")" in text:
        server_id = text.split("(")[1].split(")")[0]
        sess["edit_server_id"] = server_id
        sess["step"] = "edit_server_options"

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("تعديل الاسم", "تعديل Endpoint")
        markup.add("تعديل API Key", "إزالة API Key المخصص")
        markup.add("تعديل رابط IP", "إزالة رابط IP")
        markup.add("رجوع")

        server_info = data["servers"][server_id]
        msg = f"🖥️ تعديل الخادم: {server_info['name']}\n"
        msg += "اختر ما تريد تعديله:"
        return bot.send_message(message.chat.id, msg, reply_markup=markup)

    if sess.get("step") == "edit_server_options":
        server_id = sess["edit_server_id"]

        if text == "تعديل الاسم":
            sess["step"] = "edit_server_name"
            return bot.send_message(message.chat.id, "أدخل الاسم الجديد:")

        elif text == "تعديل Endpoint":
            sess["step"] = "edit_server_endpoint"
            return bot.send_message(message.chat.id, "أدخل Endpoint الجديد:")

        elif text == "تعديل API Key":
            sess["step"] = "edit_server_api_key"
            return bot.send_message(message.chat.id, "أدخل API Key الجديد:")

        elif text == "إزالة API Key المخصص":
            if "api_key" in data["servers"][server_id]:
                del data["servers"][server_id]["api_key"]
                save_data(data)
                user_sessions.pop(uid)
                return bot.send_message(message.chat.id, "✅ تم إزالة API Key المخصص. سيستخدم الخادم API Key الافتراضي.")
            else:
                return bot.send_message(message.chat.id, "❌ الخادم يستخدم API Key الافتراضي مسبقاً.")

        elif text == "تعديل رابط IP":
            sess["step"] = "edit_server_ip_url"
            current_url = data["servers"][server_id].get("ip_change_url", "")
            if current_url:
                msg = f"الرابط الحالي: {current_url}\nأدخل الرابط الجديد:"
            else:
                msg = "أدخل رابط تغيير IP للخادم:"
            return bot.send_message(message.chat.id, msg)

        elif text == "إزالة رابط IP":
            if "ip_change_url" in data["servers"][server_id]:
                del data["servers"][server_id]["ip_change_url"]
                save_data(data)
                user_sessions.pop(uid)
                return bot.send_message(message.chat.id, "✅ تم إزالة رابط تغيير IP للخادم.")
            else:
                return bot.send_message(message.chat.id, "❌ الخادم لا يحتوي على رابط تغيير IP.")

    if sess.get("step") == "edit_server_name":
        server_id = sess["edit_server_id"]
        data["servers"][server_id]["name"] = text.strip()
        save_data(data)
        user_sessions.pop(uid)
        return bot.send_message(message.chat.id, "✅ تم تحديث اسم الخادم بنجاح!")

    if sess.get("step") == "edit_server_endpoint":
        server_id = sess["edit_server_id"]
        data["servers"][server_id]["endpoint"] = text.strip()
        save_data(data)
        user_sessions.pop(uid)
        return bot.send_message(message.chat.id, "✅ تم تحديث Endpoint الخادم بنجاح!")

    if sess.get("step") == "edit_server_api_key":
        api_key = text.strip()
        if len(api_key) != 64:
            return bot.send_message(message.chat.id, "❌ API key يجب أن يكون 64 رمز. حاول مرة أخرى:")

        server_id = sess["edit_server_id"]
        data["servers"][server_id]["api_key"] = api_key
        save_data(data)
        user_sessions.pop(uid)
        return bot.send_message(message.chat.id, "✅ تم تحديث API Key الخادم بنجاح!")

    if sess.get("step") == "edit_server_ip_url":
        ip_url = text.strip()
        if not ip_url.startswith(("http://", "https://")):
            return bot.send_message(message.chat.id, "❌ يجب أن يبدأ الرابط بـ http:// أو https://")

        server_id = sess["edit_server_id"]
        data["servers"][server_id]["ip_change_url"] = ip_url
        save_data(data)
        user_sessions.pop(uid)
        return bot.send_message(message.chat.id, "✅ تم تحديث رابط تغيير IP للخادم بنجاح!")

    # معالجة حذف الخوادم
    if sess.get("step") == "select_server_delete" and "(" in text and ")" in text:
        server_id = text.split("(")[1].split(")")[0]

        # التحقق من عدم وجود بروكسيات تستخدم هذا الخادم
        server_in_use = False
        for user_proxies in data.get("proxies", {}).values():
            for proxy in user_proxies:
                if proxy.get("server_id") == server_id:
                    server_in_use = True
                    break
            if server_in_use:
                break

        if server_in_use:
            return bot.send_message(message.chat.id, "❌ لا يمكن حذف الخادم لأنه يحتوي على بروكسيات نشطة.")

        del data["servers"][server_id]
        save_data(data)
        user_sessions.pop(uid)
        return bot.send_message(message.chat.id, f"✅ تم حذف الخادم بنجاح!")

    # معالجة تفعيل/إلغاء الخوادم
    if sess.get("step") == "toggle_server_status" and "(" in text and ")" in text:
        server_id = text.split("(")[1].split(")")[0]
        current_status = data["servers"][server_id].get("active", True)
        data["servers"][server_id]["active"] = not current_status
        save_data(data)
        user_sessions.pop(uid)

        new_status = "تفعيل" if not current_status else "إلغاء تفعيل"
        return bot.send_message(message.chat.id, f"✅ تم {new_status} الخادم بنجاح!")

    # معالجة إضافة/تعديل روابط IP للخوادم
    if sess.get("step") == "select_server_ip_url" and "(" in text and ")" in text:
        server_id = text.split("(")[1].split(")")[0]
        sess["selected_server_ip"] = server_id
        sess["step"] = "add_server_ip_url"
        
        current_url = data["servers"][server_id].get("ip_change_url", "")
        server_name = data["servers"][server_id]["name"]
        
        if current_url:
            msg = f"🔗 الرابط الحالي للخادم {server_name}:\n{current_url}\n\nأدخل الرابط الجديد لتغيير IP:"
        else:
            msg = f"➕ إضافة رابط تغيير IP للخادم {server_name}:\nأدخل الرابط:"
        
        return bot.send_message(message.chat.id, msg)

    if sess.get("step") == "add_server_ip_url":
        server_id = sess["selected_server_ip"]
        new_url = text.strip()
        
        if not new_url.startswith(("http://", "https://")):
            return bot.send_message(message.chat.id, "❌ يجب أن يبدأ الرابط بـ http:// أو https://")
        
        data["servers"][server_id]["ip_change_url"] = new_url
        save_data(data)
        user_sessions.pop(uid)
        
        server_name = data["servers"][server_id]["name"]
        return bot.send_message(message.chat.id, f"✅ تم إضافة/تحديث رابط تغيير IP للخادم {server_name} بنجاح!")

    # معالجة حذف روابط IP للخوادم
    if sess.get("step") == "delete_server_ip_url" and "(" in text and ")" in text:
        server_id = text.split("(")[1].split(")")[0]
        
        if "ip_change_url" in data["servers"][server_id]:
            del data["servers"][server_id]["ip_change_url"]
            save_data(data)
            user_sessions.pop(uid)
            
            server_name = data["servers"][server_id]["name"]
            return bot.send_message(message.chat.id, f"✅ تم حذف رابط تغيير IP للخادم {server_name} بنجاح!")
        else:
            return bot.send_message(message.chat.id, "❌ الخادم لا يحتوي على رابط تغيير IP")

    # معالجة إيقاف السيرفر بسبب عطل
    if sess.get("step") == "select_server_maintenance" and text.startswith("🔧 "):
        try:
            # استخراج اسم السيرفر من النص
            server_text = text.replace("🔧 ", "")
            server_name = server_text.split(" (")[0]
            
            # البحث عن معرف السيرفر
            target_server_id = None
            for server_id, server_info in data["servers"].items():
                if server_info["name"] == server_name:
                    target_server_id = server_id
                    break
            
            if not target_server_id:
                return bot.send_message(message.chat.id, "❌ لم يتم العثور على السيرفر")
            
            # حساب عدد المستخدمين المتأثرين
            affected_users = []
            for user_id, user_proxies in data.get("proxies", {}).items():
                user_has_proxies_in_server = False
                for proxy in user_proxies:
                    if proxy.get("server_id", "usa1") == target_server_id:
                        user_has_proxies_in_server = True
                        break
                if user_has_proxies_in_server:
                    affected_users.append(user_id)
            
            if not affected_users:
                return bot.send_message(message.chat.id, "❌ لا يوجد مستخدمين في هذا السيرفر")
            
            # حفظ معلومات السيرفر المختار
            sess["maintenance_server_id"] = target_server_id
            sess["maintenance_server_name"] = server_name
            sess["affected_users"] = affected_users
            sess["step"] = "select_replacement_server"
            
            # عرض السيرفرات البديلة
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for server_id, server_info in data["servers"].items():
                if server_id != target_server_id and server_info.get("active", True):
                    markup.add(f"📡 {server_info['name']}")
            markup.add("رجوع")
            
            msg = f"🔧 إيقاف السيرفر: {server_name}\n"
            msg += f"👥 عدد المستخدمين المتأثرين: {len(affected_users)}\n\n"
            msg += "اختر السيرفر البديل لنقل المستخدمين إليه:"
            
            return bot.send_message(message.chat.id, msg, reply_markup=markup)
            
        except Exception as e:
            print(f"Error in server maintenance: {e}")
            return bot.send_message(message.chat.id, "❌ حدث خطأ في معالجة الطلب")

    if sess.get("step") == "select_replacement_server" and text.startswith("📡 "):
        try:
            replacement_server_name = text.replace("📡 ", "")
            
            # البحث عن معرف السيرفر البديل
            replacement_server_id = None
            for server_id, server_info in data["servers"].items():
                if server_info["name"] == replacement_server_name:
                    replacement_server_id = server_id
                    break
            
            if not replacement_server_id:
                return bot.send_message(message.chat.id, "❌ لم يتم العثور على السيرفر البديل")
            
            maintenance_server_id = sess["maintenance_server_id"]
            maintenance_server_name = sess["maintenance_server_name"]
            affected_users = sess["affected_users"]
            
            # إيقاف السيرفر الأصلي
            data["servers"][maintenance_server_id]["active"] = False
            data["servers"][maintenance_server_id]["maintenance"] = True
            data["servers"][maintenance_server_id]["maintenance_reason"] = "عطل فني"
            
            migration_summary = []
            total_migrated = 0
            
            # نقل جميع البروكسيات للمستخدمين المتأثرين
            for user_id in affected_users:
                user_proxies = data.get("proxies", {}).get(user_id, [])
                migrated_proxies = []
                
                for proxy in user_proxies[:]:  # نسخة من القائمة للتعديل الآمن
                    if proxy.get("server_id", "usa1") == maintenance_server_id:
                        try:
                            # حذف البروكسي القديم من السيرفر الأصلي
                            old_proxy_id = proxy.get("proxy_id")
                            if old_proxy_id:
                                try:
                                    old_server_info = data["servers"].get(maintenance_server_id, {})
                                    old_api_key = old_server_info.get("api_key", data["api_key"])
                                    requests.delete(
                                        f"https://iproxy.online/api/cn/v1/proxy-access/{old_proxy_id}",
                                        headers={"Authorization": f"Bearer {old_api_key}"},
                                        timeout=10
                                    )
                                except:
                                    pass  # تجاهل أخطاء حذف البروكسي القديم
                            
                            # حساب المدة المتبقية
                            try:
                                # تحويل تاريخ الانتهاء إلى كائن datetime
                                end_date_str = proxy["date_end"]
                                # إزالة (GMT+3) من النص
                                end_date_clean = end_date_str.replace(" (GMT+3)", "")
                                end_date = datetime.strptime(end_date_clean, "%Y-%m-%d %H:%M")
                                
                                # حساب المدة المتبقية بالدقائق
                                now = datetime.now()
                                time_remaining = end_date - now
                                minutes_remaining = max(1, int(time_remaining.total_seconds() / 60))
                                
                                # إنشاء بروكسي جديد في السيرفر البديل
                                new_proxy = create_proxy(
                                    data["api_key"], 
                                    proxy["type"], 
                                    minutes_remaining,
                                    username=proxy.get("login"),
                                    password=proxy.get("password"),
                                    ip=None,
                                    with_api=proxy.get("with_api", False),
                                    server_id=replacement_server_id
                                )
                                
                                if "error" not in new_proxy:
                                    # إضافة معلومات إضافية
                                    new_proxy['with_api'] = proxy.get('with_api', False)
                                    new_proxy['migrated_from'] = maintenance_server_id
                                    new_proxy['migration_date'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                                    
                                    # إزالة البروكسي القديم وإضافة الجديد
                                    data["proxies"][user_id].remove(proxy)
                                    data["proxies"][user_id].append(new_proxy)
                                    
                                    migrated_proxies.append({
                                        "old_server": maintenance_server_name,
                                        "new_server": replacement_server_name,
                                        "type": proxy["type"],
                                        "remaining_time": f"{minutes_remaining // (60*24)} أيام {(minutes_remaining % (60*24)) // 60} ساعات"
                                    })
                                    total_migrated += 1
                                    
                            except Exception as e:
                                print(f"Error calculating remaining time for user {user_id}: {e}")
                                continue
                                
                        except Exception as e:
                            print(f"Error migrating proxy for user {user_id}: {e}")
                            continue
                
                # إرسال إشعار للمستخدم
                if migrated_proxies:
                    try:
                        user_msg = "🔧 إشعار هام: تم إيقاف السيرفر بسبب عطل فني\n"
                        user_msg += "━━━━━━━━━━━━━━\n"
                        user_msg += f"📡 السيرفر المتوقف: {maintenance_server_name}\n"
                        user_msg += f"📡 السيرفر الجديد: {replacement_server_name}\n"
                        user_msg += f"🔄 تم نقل {len(migrated_proxies)} بروكسي\n\n"
                        
                        user_msg += "📋 تفاصيل البروكسيات المنقولة:\n"
                        for i, migrated in enumerate(migrated_proxies, 1):
                            user_msg += f"{i}. نوع: {migrated['type'].upper()}\n"
                            user_msg += f"   المدة المتبقية: {migrated['remaining_time']}\n"
                            if i < len(migrated_proxies):
                                user_msg += "───────────────\n"
                        
                        user_msg += "\n✅ تم الحفاظ على جميع المدد المتبقية\n"
                        user_msg += "📞 للاستفسار: @WorkTrekSupport"
                        
                        bot.send_message(user_id, user_msg)
                        
                        migration_summary.append(f"👤 {user_id}: {len(migrated_proxies)} بروكسي")
                        
                    except Exception as e:
                        print(f"Error sending notification to user {user_id}: {e}")
            
            save_data(data)
            user_sessions.pop(uid)
            
            # إرسال تقرير للأدمن
            admin_msg = "✅ تم إيقاف السيرفر ونقل المستخدمين بنجاح\n"
            admin_msg += "━━━━━━━━━━━━━━\n"
            admin_msg += f"🔧 السيرفر المتوقف: {maintenance_server_name}\n"
            admin_msg += f"📡 السيرفر البديل: {replacement_server_name}\n"
            admin_msg += f"👥 عدد المستخدمين: {len(affected_users)}\n"
            admin_msg += f"🔄 إجمالي البروكسيات المنقولة: {total_migrated}\n\n"
            
            if migration_summary:
                admin_msg += "📊 ملخص النقل:\n"
                for summary in migration_summary[:10]:  # عرض أول 10 مستخدمين
                    admin_msg += f"{summary}\n"
                if len(migration_summary) > 10:
                    admin_msg += f"و {len(migration_summary) - 10} مستخدمين آخرين..."
            
            return bot.send_message(message.chat.id, admin_msg)
            
        except Exception as e:
            print(f"Error in server migration: {e}")
            return bot.send_message(message.chat.id, f"❌ حدث خطأ أثناء النقل: {str(e)}")

    if sess.get("step") == "update_exchange_rate":
        try:
            exchange_rate = float(text)
            currency = sess["currency"]
            if "exchange_rates" not in data:
                data["exchange_rates"] = {}

            data["exchange_rates"][currency] = exchange_rate
            save_data(data)
            user_sessions.pop(uid)
            return bot.send_message(message.chat.id, f"تم تحديث سعر الصرف بنجاح إلى {exchange_rate}")
        except:
            return bot.send_message(message.chat.id, "الرجاء إدخال رقم صحيح")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    uid = str(call.from_user.id)
    if call.data.startswith("user_info:") or call.data.startswith("refresh_user:"):
        user_id = call.data.split(":")[1]
        try:
            user = bot.get_chat(int(user_id))
            if not user:
                bot.answer_callback_query(call.id, "لم يتم العثور على المستخدم")
                return

            current_text = call.message.text if call.message.text else ""
            new_stats = f"👤 معلومات المستخدم\n"
            new_stats += "━━━━━━━━━━━━━━\n"
            new_stats += f"الاسم: {user.first_name or 'غير معروف'}\n"
            new_stats += f"المعرف: @{user.username}\n" if user.username else "المعرف: لا يوجد\n"
            new_stats += f"الآيدي: {user_id}\n"
            new_stats += f"الرصيد: {data['balance'].get(user_id, 0)}$\n"
            new_stats += "━━━━━━━━━━━━━━\n"

            user_proxies = data["proxies"].get(user_id, [])
            if user_proxies:
                new_stats += f"📊 البروكسيات النشطة ({len(user_proxies)}):\n\n"
                for i, proxy in enumerate(user_proxies, 1):
                    new_stats += f"{i}. نوع: {proxy['type'].upper()}\n"
                    new_stats += f"   IP: {proxy['ip']}\n"
                    new_stats += f"   المنفذ: {proxy['port']}\n"
                    new_stats += f"   ينتهي في: {proxy['date_end']}\n"
                    if i < len(user_proxies):
                        new_stats += "───────────────\n"
            else:
                new_stats += "📊 لا توجد بروكسيات نشطة"

            if current_text != new_stats:
                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton("➕ إضافة رصيد", callback_data=f"add_balance:{user_id}"),
                    types.InlineKeyboardButton("➖ خصم رصيد", callback_data=f"remove_balance:{user_id}")
                )

                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=new_stats,
                    reply_markup=markup
                )
            bot.answer_callback_query(call.id)
        except Exception as e:
            print(f"Error in callback query: {e}")
            bot.answer_callback_query(call.id, "حدث خطأ في عرض معلومات المستخدم")

    elif call.data.startswith(("add_balance:", "remove_balance:")):
        action, user_id = call.data.split(":")
        if uid not in user_sessions:
            user_sessions[uid] = {}
        user_sessions[uid].update({
            "step": "balance_amount",
            "action": "add" if action == "add_balance" else "subtract",
            "target_id": user_id
        })
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "أدخل المبلغ:")

    elif call.data.startswith("change_ip:"):
        proxy_id = call.data.split(":")[1]
        user_sessions[uid] = {
            "step": "update_ip",
            "proxy_id": proxy_id
        }
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "أرسل الـ IP الجديد:")

    elif call.data.startswith("change_real_ip:"):
        proxy_id = call.data.split(":")[1]
        try:
            proxies = data.get("proxies", {}).get(uid, [])
            proxy = next((p for p in proxies if p['proxy_id'] == proxy_id), None)

            if not proxy:
                return bot.answer_callback_query(call.id, "❌ البروكسي غير موجود", show_alert=True)

            can_change, message = can_change_ip(proxy, uid)
            if not can_change:
                return bot.answer_callback_query(call.id, message, show_alert=True)

            if proxy.get('has_api'):
                try:
                    # الحصول على رابط تغيير IP الخاص بالخادم
                    server_id = proxy.get("server_id", "usa1")
                    server_info = data["servers"].get(server_id, {})
                    update_url = server_info.get("ip_change_url", "")
                    
                    if not update_url:
                        # محاولة استخدام الرابط العام القديم إذا لم يوجد رابط خاص بالخادم
                        update_url = data.get("ip_change_url", "")
                        if not update_url:
                            bot.answer_callback_query(call.id, "❌ رابط تغيير IP غير متوفر لهذا الخادم", show_alert=True)
                            return

                    response = requests.get(update_url, timeout=20)
                    if response.status_code == 200:
                        update_last_ip_change(proxy)
                        save_data(data)
                        time.sleep(3)
                        bot.answer_callback_query(call.id, "✅ تم تغيير IP بنجاح")
                        bot.send_message(call.message.chat.id, "✅ تم تغيير IP بنجاح")
                    else:
                        return bot.answer_callback_query(call.id, f"❌ فشل تغيير IP: {response.status_code}", show_alert=True)
                except Exception as e:
                    print(f"Error updating real IP: {e}")
                    bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء تغيير عنوان IP الحقيقي", show_alert=True)
            else:
                bot.answer_callback_query(call.id, "❌ هذا البروكسي لا يدعم تغيير IP", show_alert=True)
        except Exception as e:
            print(f"Error changing real IP: {e}")
            bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء تغيير IP", show_alert=True)
    elif call.data.startswith("view_proxy:"):
        proxy_id = call.data.split(":")[1]
        proxies = data.get("proxies", {}).get(uid, [])
        proxy = next((p for p in proxies if p['proxy_id'] == proxy_id), None)

        if proxy:
            msg = "🔐 معلومات البروكسي:\n"
            msg += "━━━━━━━━━━━━━━\n"
            msg += f"📡 النوع: {proxy['type'].upper()}\n"
            msg += f"🖥️ الخادم: {proxy.get('server_name', 'غير محدد')}\n"
            msg += f"🌐 IP: `{proxy['ip']}`\n"
            msg += f"🔌 Port: `{proxy['port']}`\n"
            if proxy.get('login'):
                msg += f"👤 المستخدم: `{proxy['login']}`\n"
                msg += f"🔑 كلمة المرور: `{proxy['password']}`\n"
            msg += f"⏰ ينتهي في: {proxy['date_end']}\n"
            msg += f"📅 تم الإنشاء: {proxy['created']}\n"

            markup = types.InlineKeyboardMarkup(row_width=1)

            # إضافة خيارات تغيير IP حسب نوع البروكسي
            if proxy['type'] == 'inject':
                markup.add(types.InlineKeyboardButton(
                    "🔄 تغيير IP whitelist",
                    callback_data=f"change_ip:{proxy_id}"
                ))

            # إضافة خيار تغيير IP الحقيقي فقط للبروكسيات التي تم شراؤها مع هذه الخاصية
            if proxy.get('has_api') and proxy.get('with_api'):
                markup.add(types.InlineKeyboardButton(
                    "🔄 تغيير عنوان IP الحقيقي",
                    callback_data=f"change_real_ip:{proxy_id}"
                ))

            # إضافة خيار تبديل البروكسي لمرة واحدة (إذا لم يتم تبديله من قبل)
            if not proxy.get('swapped', False):
                markup.add(types.InlineKeyboardButton(
                    "🔄 تبديل البروكسي لمرة واحدة",
                    callback_data=f"swap_proxy:{proxy_id}"
                ))

            markup.add(types.InlineKeyboardButton(
                "🔙 رجوع",
                callback_data="back_to_proxy_list"
            ))

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=msg,
                reply_markup=markup,
                parse_mode="Markdown"
            )

    elif call.data.startswith("swap_proxy:"):
        proxy_id = call.data.split(":")[1]
        proxies = data.get("proxies", {}).get(uid, [])
        proxy = next((p for p in proxies if p['proxy_id'] == proxy_id), None)

        if not proxy:
            bot.answer_callback_query(call.id, "❌ البروكسي غير موجود", show_alert=True)
            return

        if proxy.get('swapped', False):
            bot.answer_callback_query(call.id, "❌ تم تبديل هذا البروكسي من قبل", show_alert=True)
            return

        # حساب المدة المتبقية
        remaining_minutes = calculate_remaining_minutes(proxy)
        current_server_id = proxy.get("server_id", "usa1")
        current_server_name = proxy.get("server_name", "غير محدد")

        # عرض الخوادم المتاحة (باستثناء الخادم الحالي)
        available_servers = []
        for server_id, server_info in data["servers"].items():
            if (server_id != current_server_id and 
                server_info.get("active", True) and 
                not server_info.get("maintenance", False)):
                available_servers.append((server_id, server_info["name"]))

        if not available_servers:
            bot.answer_callback_query(call.id, "❌ لا توجد خوادم أخرى متاحة للتبديل", show_alert=True)
            return

        # حفظ معلومات البروكسي للتبديل
        user_sessions[uid] = {
            "step": "select_swap_server",
            "swap_proxy_id": proxy_id,
            "remaining_minutes": remaining_minutes,
            "available_servers": available_servers
        }

        markup = types.InlineKeyboardMarkup(row_width=1)
        for server_id, server_name in available_servers:
            markup.add(types.InlineKeyboardButton(
                f"📡 {server_name}",
                callback_data=f"confirm_swap:{server_id}"
            ))
        markup.add(types.InlineKeyboardButton(
            "❌ إلغاء",
            callback_data=f"view_proxy:{proxy_id}"
        ))

        remaining_days = remaining_minutes // (60*24)
        remaining_hours = (remaining_minutes % (60*24)) // 60

        msg = "🔄 تبديل البروكسي لمرة واحدة\n"
        msg += "━━━━━━━━━━━━━━\n"
        msg += f"📡 الخادم الحالي: {current_server_name}\n"
        msg += f"⏰ المدة المتبقية: {remaining_days} أيام و {remaining_hours} ساعة\n"
        msg += "━━━━━━━━━━━━━━\n"
        msg += "⚠️ تنبيه: يمكن التبديل مرة واحدة فقط!\n"
        msg += "اختر الخادم الجديد:"

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=msg,
            reply_markup=markup
        )

    elif call.data.startswith("confirm_swap:"):
        new_server_id = call.data.split(":")[1]
        sess = user_sessions.get(uid, {})
        
        if sess.get("step") != "select_swap_server":
            bot.answer_callback_query(call.id, "❌ خطأ في العملية", show_alert=True)
            return

        proxy_id = sess["swap_proxy_id"]
        remaining_minutes = sess["remaining_minutes"]
        
        proxies = data.get("proxies", {}).get(uid, [])
        old_proxy = next((p for p in proxies if p['proxy_id'] == proxy_id), None)

        if not old_proxy:
            bot.answer_callback_query(call.id, "❌ البروكسي غير موجود", show_alert=True)
            return

        try:
            # إنشاء بروكسي جديد في الخادم الجديد
            new_proxy = create_proxy(
                data["api_key"], 
                old_proxy["type"], 
                remaining_minutes,
                username=old_proxy.get("login"),
                password=old_proxy.get("password"),
                ip=None,
                with_api=old_proxy.get("with_api", False),
                server_id=new_server_id
            )

            if "error" in new_proxy:
                bot.answer_callback_query(call.id, f"❌ فشل إنشاء البروكسي الجديد: {new_proxy['error']}", show_alert=True)
                return

            # حذف البروكسي القديم من الخادم
            try:
                old_server_id = old_proxy.get("server_id", "usa1")
                old_server_info = data["servers"].get(old_server_id, {})
                old_api_key = old_server_info.get("api_key", data["api_key"])
                
                requests.delete(
                    f"https://iproxy.online/api/cn/v1/proxy-access/{proxy_id}",
                    headers={"Authorization": f"Bearer {old_api_key}"},
                    timeout=10
                )
            except Exception as e:
                print(f"Error deleting old proxy: {e}")

            # تحديث معلومات البروكسي الجديد
            new_proxy['with_api'] = old_proxy.get('with_api', False)
            new_proxy['swapped'] = True  # تسجيل أن البروكسي تم تبديله
            new_proxy['original_server'] = old_proxy.get("server_name", "غير محدد")
            new_proxy['swap_date'] = datetime.now().strftime("%Y-%m-%d %H:%M")

            # إزالة البروكسي القديم وإضافة الجديد
            data["proxies"][uid].remove(old_proxy)
            data["proxies"][uid].append(new_proxy)
            save_data(data)

            user_sessions.pop(uid, None)

            msg = "✅ تم تبديل البروكسي بنجاح!\n"
            msg += "━━━━━━━━━━━━━━\n"
            msg += f"📡 الخادم الجديد: {new_proxy.get('server_name', 'غير محدد')}\n"
            msg += f"🌐 IP الجديد: `{new_proxy['ip']}`\n"
            msg += f"🔌 Port الجديد: `{new_proxy['port']}`\n"
            if new_proxy.get('login'):
                msg += f"👤 المستخدم: `{new_proxy['login']}`\n"
                msg += f"🔑 كلمة المرور: `{new_proxy['password']}`\n"
            msg += f"⏰ ينتهي في: {new_proxy['date_end']}\n"
            msg += "━━━━━━━━━━━━━━\n"
            msg += "⚠️ لا يمكن تبديل هذا البروكسي مرة أخرى"

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(
                "🔙 رجوع للقائمة الرئيسية",
                callback_data="back_to_proxy_list"
            ))

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=msg,
                reply_markup=markup,
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id, "✅ تم التبديل بنجاح!")

        except Exception as e:
            print(f"Error swapping proxy: {e}")
            bot.answer_callback_query(call.id, f"❌ حدث خطأ أثناء التبديل: {str(e)}", show_alert=True)

    elif call.data == "back_to_proxy_list":
        proxies = data.get("proxies", {}).get(uid, [])
        markup = types.InlineKeyboardMarkup(row_width=1)
        for i, p in enumerate(sorted(proxies, key=lambda x: x["created"], reverse=True), 1):
            button_text = f"🔐 بروكسي {p['type'].upper()} - {p['port']}"
            if p.get('has_api'):
                button_text += " 🔄"
            if p.get('swapped'):
                button_text += " 🔄✅"
            markup.add(types.InlineKeyboardButton(
                button_text,
                callback_data=f"view_proxy:{p['proxy_id']}"
            ))
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="📋 اختر بروكسي لعرض معلوماته:",
            reply_markup=markup
        )

    elif call.data.startswith("view_deposit:"):
        deposit_id = call.data.split(":")[1]
        deposit = data["pending_deposits"].get(deposit_id)

        if deposit and deposit["status"] == "pending":
            try:
                user = bot.get_chat(int(deposit["user_id"]))
                user_name = user.first_name if user else "غير معروف"
                username = f"@{user.username}" if user and user.username else "لا يوجد معرف"

                msg = "📝 تفاصيل طلب الإيداع:\n"
                msg += "━━━━━━━━━━━━━━\n"
                msg += f"💰 المبلغ: {deposit['amount']}$\n"
                msg += f"💳 طريقة الدفع: {data['payment_methods'][deposit['method']]['name']}\n"
                msg += f"👤 اسم المستخدم: {user_name}\n"
                msg += f"📧 معرف المستخدم: {username}\n"
                msg += f"🆔 معرف العملية: {deposit['transaction_id']}\n"
                msg += f"📅 التاريخ: {deposit['date']}\n"
                msg += "━━━━━━━━━━━━━━"

                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton("✅ قبول", callback_data=f"approve_deposit:{deposit_id}"),
                    types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_deposit:{deposit_id}"),
                    types.InlineKeyboardButton("تعديل المبلغ", callback_data=f"edit_deposit:{deposit_id}")
                )

                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=msg,
                    reply_markup=markup
                )
            except Exception as e:
                print(f"Error showing deposit details: {e}")
                bot.answer_callback_query(call.id, "حدث خطأ في عرض التفاصيل")

    elif call.data.startswith("edit_deposit:"):
        deposit_id = call.data.split(":")[1]
        deposit = data["pending_deposits"].get(deposit_id)

        if deposit and deposit["status"] == "pending":
            user_sessions[uid] = {
                "step": "edit_deposit_amount",
                "deposit_id": deposit_id
            }
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "أدخل المبلغ الجديد:")
        else:
            bot.answer_callback_query(call.id, "الطلب غير موجود أو تم معالجته مسبقاً")

    elif call.data.startswith("approve_deposit:"):
        deposit_id = call.data.split(":")[1]
        deposit = data["pending_deposits"].get(deposit_id)

        if deposit and deposit["status"] == "pending":
            deposit["status"] = "approved"
            update_balance(deposit["user_id"], deposit["amount"])
            save_data(data)

            # إرسال إشعار للمستخدم
            user_msg = "✅ تم قبول طلب الإيداع\n"
            user_msg += "━━━━━━━━━━━━━━\n"
            user_msg += f"💰 المبلغ: {deposit['amount']}$\n"
            user_msg += f"🧾 رقم الطلب: {deposit_id}\n"
            user_msg += f"💰 رصيدك الحالي: {data['balance'][deposit['user_id']]}$"

            bot.send_message(deposit["user_id"], user_msg)
            bot.answer_callback_query(call.id, "تم قبول الطلب وإضافة الرصيد")
            bot.delete_message(call.message.chat.id, call.message.message_id)

    elif call.data.startswith("reject_deposit:"):
        deposit_id = call.data.split(":")[1]
        deposit = data["pending_deposits"].get(deposit_id)

        if deposit and deposit["status"] == "pending":
            deposit["status"] = "rejected"
            save_data(data)

            # إرسال إشعار للمستخدم
            user_msg = "❌ تم رفض طلب الإيداع\n"
            user_msg += "━━━━━━━━━━━━━━\n"
            user_msg += f"💰 المبلغ: {deposit['amount']}$\n"
            user_msg += f"🧾 رقم الطلب: {deposit_id}\n"
            user_msg += "يرجى التواصل مع الدعم الفني"

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📞 تواصل مع الدعم", url="https://t.me/WorkTrekSupport"))

            bot.send_message(deposit["user_id"], user_msg, reply_markup=markup)
            bot.answer_callback_query(call.id, "تم رفض الطلب")
            bot.delete_message(call.message.chat.id, call.message.message_id)

    elif call.data == "back_admin_menu":
        start(call.message)

    elif sess.get("step") == "update_api" and uid == str(ADMIN_ID):
        new_api_key = text.strip()
        if len(new_api_key) != 64:
            return bot.send_message(call.message.chat.id, "❌ مفتاح API يجب أن يكون 64 رمز.")
        data["api_key"] = new_api_key
        save_data(data)
        user_sessions.pop(uid)
        return bot.send_message(call.message.chat.id, "✅ تم تحديث مفتاح API بنجاح")

print("Bot is running...")
while True:
    try:
        bot.polling(none_stop=True, timeout=60)
    except Exception as e:
        print(f"Connection error occurred: {e}")
        time.sleep(3)
        continue
