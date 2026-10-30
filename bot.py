import os, random, asyncio, logging, sqlite3
from datetime import datetime, timezone
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ChatType
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import edge_tts

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL = os.getenv("REQUIRED_CHANNEL", "@Mb_silk").strip()
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/Mb_silk").strip()
AD_INTERVAL_HOURS = int(os.getenv("AD_INTERVAL_HOURS", "12"))
VOICE_NAME = os.getenv("VOICE_NAME", "fa-IR-DilaraNeural")
AI_API_KEY = os.getenv("AI_API_KEY", "").strip()
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").strip()
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini").strip()

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Copy .env.example to .env and add your token.")

logging.basicConfig(level=logging.INFO)
bot = Bot(TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()
DB = "dardesar.sqlite3"

def db():
    return sqlite3.connect(DB)

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS groups
            (chat_id INTEGER PRIMARY KEY, title TEXT, enabled INTEGER DEFAULT 1,
             voice_percent INTEGER DEFAULT 35, ads_enabled INTEGER DEFAULT 1,
             last_ad TEXT)""")
        con.execute("""CREATE TABLE IF NOT EXISTS users
            (user_id INTEGER PRIMARY KEY, joined_at TEXT)""")

def is_admin(message: Message):
    return message.from_user and message.from_user.id in set(
        int(x) for x in os.getenv("BOT_OWNERS", "").split(",") if x.strip().isdigit()
    )

async def member_ok(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        logging.exception("Could not check channel membership")
        return False

async def gate(message: Message) -> bool:
    if message.chat.type == ChatType.PRIVATE and message.from_user:
        if await member_ok(message.from_user.id):
            return True
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="عضویت در کانال 🖤", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="عضو شدم؛ بررسی کن", callback_data="check_join")]
        ])
        await message.answer("اول عضو کانال شو تا خانوم دردسر برات فعال بشه 😈", reply_markup=kb)
        return False
    return True

@dp.callback_query(F.data == "check_join")
async def check_join(call: CallbackQuery):
    if call.from_user and await member_ok(call.from_user.id):
        await call.message.edit_text("خوش اومدی! حالا می‌تونی از امکانات خانوم دردسر استفاده کنی 🖤")
    else:
        await call.answer("هنوز عضویتت تأیید نشده؛ اول عضو کانال شو.", show_alert=True)

@dp.message(CommandStart())
async def start(message: Message):
    if not await gate(message):
        return
    await message.answer(
        "سلام! من خانوم دردسرم 😈🖤\n"
        "برای گروهت منو اضافه کن و دسترسی‌های لازم رو بده.\n\n"
        "/help — راهنما\n"
        "/challenge — چالش\n"
        "/truth — جرئت یا حقیقت (حقیقت)\n"
        "/dare — جرئت"
    )

@dp.message(Command("help"))
async def help_cmd(message: Message):
    if not await gate(message):
        return
    await message.answer(
        "راهنمای خانوم دردسر 🖤\n"
        "/challenge چالش روز\n/truth سؤال حقیقت\n/dare جرئت\n"
        "/voice_test تست ویس (در گفتگوی خصوصی)\n"
        "مدیر گروه: /ads_on یا /ads_off برای تبلیغات"
    )

CHALLENGES = [
    "بدون فکر کردن، سه تا از عجیب‌ترین عادت‌هات رو بگو 😂",
    "آخرین آهنگی که گوش دادی چی بود؟",
    "اگه یک روز نامرئی بودی، اولین کارت چی بود؟",
    "از بین اعضای گروه، کی بیشتر احتمال داره نصفه‌شب بیدار بمونه؟ 😈",
    "یک اعتراف بی‌خطر و خنده‌دار بکن!"
]
TRUTHS = [
    "آخرین باری که از خنده روده‌بُر شدی کی بود؟",
    "تا حالا پیام دادی و سریع پشیمون شدی؟",
    "عجیب‌ترین غذایی که دوست داری چیه؟"
]
DARES = [
    "تا پنج دقیقه فقط با ایموجی جواب بده 😂",
    "برای یکی از اعضا یک تعریف واقعی و محترمانه بنویس.",
    "یک جمله خیلی جدی با لحن گوینده اخبار بفرست!"
]

@dp.message(Command("challenge"))
async def challenge(message: Message):
    if await gate(message):
        await message.answer("🎯 چالش خانوم دردسر:\n" + random.choice(CHALLENGES))

@dp.message(Command("truth"))
async def truth(message: Message):
    if await gate(message):
        await message.answer("🖤 حقیقت:\n" + random.choice(TRUTHS))

@dp.message(Command("dare"))
async def dare(message: Message):
    if await gate(message):
        await message.answer("😈 جرئت:\n" + random.choice(DARES))

async def make_voice(text: str, filename: str):
    communicate = edge_tts.Communicate(text, VOICE_NAME, rate="+3%", pitch="+2Hz")
    await communicate.save(filename)

@dp.message(Command("voice_test"))
async def voice_test(message: Message):
    if not await gate(message):
        return
    if message.chat.type != ChatType.PRIVATE:
        await message.answer("برای تست ویس، توی خصوصی خودم دستور /voice_test رو بفرست.")
        return
    path = "voice_test.mp3"
    try:
        await make_voice("سلام عزیزم! من خانوم دردسرم. آماده‌ای گروه رو از سکوت دربیاریم؟", path)
        from aiogram.types import FSInputFile
        await message.answer_voice(FSInputFile(path), caption="صدای آزمایشی خانوم دردسر 🖤")
    except Exception:
        logging.exception("TTS failed")
        await message.answer("فعلاً ساخت ویس انجام نشد. اتصال اینترنت یا سرویس صدا رو بررسی کن.")
    finally:
        if os.path.exists(path):
            os.remove(path)

async def ai_reply(text: str) -> str | None:
    if not AI_API_KEY:
        return None
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)
        response = await client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content":
                 "تو خانوم دردسر هستی؛ یک شخصیت فارسی‌زبان، زنانه، شوخ، خودمانی و کمی دارک. "
                 "محترمانه و کوتاه جواب بده. توهین، آزار، محتوای جنسی صریح، تهدید یا افشای اطلاعات خصوصی نکن. "
                 "اگر بحث حساس یا خطرناک است، آرام و مسئولانه پاسخ بده. معمولاً 1 تا 3 جمله."},
                {"role": "user", "content": text[:2500]}
            ],
            max_tokens=180, temperature=0.9
        )
        return response.choices[0].message.content.strip()
    except Exception:
        logging.exception("AI request failed")
        return None

def should_answer(message: Message) -> bool:
    if not message.text or message.text.startswith("/"):
        return False
    text = message.text.lower()
    bot_username = os.getenv("BOT_USERNAME", "KhanoomDardesarBot").lower()
    direct = (message.reply_to_message and message.reply_to_message.from_user
              and message.reply_to_message.from_user.username
              and message.reply_to_message.from_user.username.lower() == bot_username)
    mention = "خانوم دردسر" in text or "خانوم‌دردسر" in text or ("@" + bot_username) in text
    # Conservative mode: answer only when addressed, to avoid flooding group chat.
    return bool(direct or mention)

@dp.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}), F.text)
async def group_chat(message: Message):
    title = message.chat.title or "گروه"
    with db() as con:
        con.execute("INSERT OR IGNORE INTO groups(chat_id,title) VALUES(?,?)",
                    (message.chat.id, title))
    if not should_answer(message):
        return
    # Enforce channel membership for people who use the assistant inside groups too.
    if message.from_user and not await member_ok(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="عضویت در کانال 🖤", url=CHANNEL_URL)]
        ])
        await message.reply("برای استفاده از خانوم دردسر اول باید عضو کانال بشی 😈", reply_markup=kb)
        return
    answer = await ai_reply(message.text)
    if not answer:
        answer = random.choice([
            "اوه اوه، بحث داره جالب می‌شه! ادامه بده ببینم 😈",
            "من اومدم وسط بحث؛ کسی چای می‌خواد؟ 😂",
            "این یکی ارزش بررسی داشت... بیشتر توضیح بده 🖤"
        ])
    with db() as con:
        row = con.execute("SELECT voice_percent FROM groups WHERE chat_id=?",
                          (message.chat.id,)).fetchone()
    voice_percent = row[0] if row else 35
    if random.randint(1, 100) <= voice_percent:
        path = f"reply_{message.chat.id}.mp3"
        try:
            await make_voice(answer, path)
            from aiogram.types import FSInputFile
            await message.answer_voice(FSInputFile(path), caption="خانوم دردسر 🎙️")
        except Exception:
            await message.reply(answer)
        finally:
            if os.path.exists(path):
                os.remove(path)
    else:
        await message.reply(answer)

@dp.message(Command("ads_on"))
async def ads_on(message: Message):
    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in ("administrator", "creator"):
        return await message.reply("این دستور فقط برای مدیران گروهه.")
    with db() as con:
        con.execute("INSERT INTO groups(chat_id,title,ads_enabled) VALUES(?,?,1) "
                    "ON CONFLICT(chat_id) DO UPDATE SET ads_enabled=1",
                    (message.chat.id, message.chat.title or "گروه"))
    await message.reply("تبلیغات کانال با فاصله زمانی فعال شد 🖤")

@dp.message(Command("ads_off"))
async def ads_off(message: Message):
    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in ("administrator", "creator"):
        return await message.reply("این دستور فقط برای مدیران گروهه.")
    with db() as con:
        con.execute("UPDATE groups SET ads_enabled=0 WHERE chat_id=?", (message.chat.id,))
    await message.reply("تبلیغات این گروه غیرفعال شد.")

async def advertise():
    with db() as con:
        groups = con.execute("SELECT chat_id FROM groups WHERE ads_enabled=1").fetchall()
    for (chat_id,) in groups:
        try:
            await bot.send_message(
                chat_id,
                "🖤 یه سر به کانال ما بزن؛ محتوای جذاب منتظرته:\n"
                f"{CHANNEL_URL}\n\nبرای توقف تبلیغات مدیر گروه می‌تونه /ads_off رو بزنه."
            )
            await asyncio.sleep(1)
        except Exception:
            logging.exception("Ad failed for %s", chat_id)

async def main():
    init_db()
    scheduler.add_job(advertise, "interval", hours=AD_INTERVAL_HOURS)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
