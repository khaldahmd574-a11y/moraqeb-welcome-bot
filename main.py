import os
import asyncio
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from hydrogram import Client, filters
from hydrogram.types import Message, ChatPermissions, ChatMemberUpdated

# =========================================================
# KEEP ALIVE SERVER
# =========================================================

class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Moraqeb & Welcome Bot is Active!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), DummyServer)
    server.serve_forever()

# =========================================================
# CONFIGURATION & CONSTANTS
# =========================================================

API_ID = int(os.environ.get("TELEGRAM_API_ID", 39120728))
API_HASH = os.environ.get("TELEGRAM_API_HASH", "1deec8393ce5aa05c54c0c7e280377d4").strip()
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

BLOCKED_KEYWORDS = [
    "سكس", "افلام اباحيه", "مؤخره", "انيك", "عارك", "سكليف", "سكاليف", "صحتي",
    "دخل يومي", "دخل خاص", "اجازه مرضيه", "اجازات مرضيه", "تقارير طبيه",
    "تقرير طبي", "والاعذار", "الاعذار", "مناهل", "تطلع اجازات", "اجازات مرضية",
    "وتقارير طبية", "مرافق مريض", "مشهد مراجعة", "تدليك الجسم", "يبغى فلوس",
    "اجازه", "تقارير", "طبيه", "مرضيه", "الاجازات"
]

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[\u064B-\u0652]", "", text)
    text = re.sub(r"[أإآ]", "ا", text)
    text = re.sub(r"ة", "ه", text)
    text = re.sub(r"ى", "ي", text)
    return text

NORMALIZED_BLOCKED = [normalize_text(word) for word in BLOCKED_KEYWORDS]
URL_PATTERN = re.compile(r"(https?://\S+|t\.me/\S+|telegram\.me/\S+)", re.IGNORECASE)

# =========================================================
# HELPER FUNCTIONS
# =========================================================

async def delete_message_after_delay(client: Client, chat_id: int, message_id: int, delay: int = 60):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id=chat_id, message_ids=message_id)
    except Exception:
        pass

# =========================================================
# MAIN BOT ENGINE
# =========================================================

async def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()

    bot = Client(
        "unified_moderation_welcome_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        in_memory=True
    )

    @bot.on_chat_member_updated()
    async def welcome_new_member(client: Client, chat_member: ChatMemberUpdated):
        if chat_member.new_chat_member and not chat_member.old_chat_member:
            user = chat_member.new_chat_member.user
            if not user or user.is_bot:
                return

            try:
                member_info = await client.get_chat_member(chat_member.chat.id, user.id)
                if member_info.status.value in ["administrator", "owner"]:
                    return
            except Exception:
                pass

            name = user.first_name or "مستخدم"
            welcome_text = (
                f"✨ يا هلا بـ ({name}) 🤍\n"
                f"🌷 نورت/ي وشرفت/ي، حياك الله بيننا 🙏🏻\n"
                f"🤍 سعداء بخدمتك دائمًا ✨"
            )

            try:
                msg = await client.send_message(chat_id=chat_member.chat.id, text=welcome_text)
                asyncio.create_task(delete_message_after_delay(client, chat_member.chat.id, msg.id, 60))
            except Exception:
                pass

    @bot.on_message(filters.group & ~filters.service)
    async def moderate_messages(client: Client, message: Message):
        if not message.from_user:
            return

        try:
            member = await client.get_chat_member(message.chat.id, message.from_user.id)
            if member.status.value in ["administrator", "owner"]:
                return
        except Exception:
            pass

        raw_text = message.text or message.caption or ""
        searchable_text = normalize_text(raw_text)

        has_link = bool(URL_PATTERN.search(raw_text))
        has_blocked_word = any(word in searchable_text for word in NORMALIZED_BLOCKED)

        if has_link or has_blocked_word:
            try:
                await message.delete()

                await client.restrict_chat_member(
                    chat_id=message.chat.id,
                    user_id=message.from_user.id,
                    permissions=ChatPermissions()
                )

                reason = "إرسال رابط" if has_link else "استخدام كلمات محظورة"
                user_name = message.from_user.first_name or "المستخدم"
                user_mention = message.from_user.mention(user_name)
                
                warning_msg = await client.send_message(
                    chat_id=message.chat.id,
                    text=f"🔇 تم كتم {user_mention} بسبب {reason}."
                )

                asyncio.create_task(delete_message_after_delay(client, message.chat.id, warning_msg.id, 60))

            except Exception:
                pass

    await bot.start()
    print("✅ تم تشغيل بوت المراقب والترحيب الموحد بنجاح!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
