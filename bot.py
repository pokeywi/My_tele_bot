from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import insert_video, search_videos, create_db, get_video_by_id
import re, time, math, requests, asyncio

api_id = 23326032
api_hash = "508102b04eccd2fff846b58516e0dbee"
bot_token = "8114721161:AAGYMYrdMm5pYso-hdnomPP52sRQpfkA3E8"
OMDB_API_KEY = "ab31838"

app = Client("bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)
create_db()

RESULTS_PER_PAGE = 5
search_cache = {}

def clean_title(title):
    title = title.replace("🎬", "")
    return re.sub(r'\.(mp4|mkv|avi|webm)$', '', title.strip(), flags=re.IGNORECASE).lower()

def format_size(size):
    if not size:
        return "غير معروف"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024

def get_movie_info(title, api_key=OMDB_API_KEY):
    try:
        url = f"http://www.omdbapi.com/?apikey={api_key}&t={title}"
        res = requests.get(url)
        data = res.json()
        if data.get("Response") == "True":
            return {
                "title": data.get("Title"),
                "year": data.get("Year"),
                "plot": data.get("Plot"),
                "rating": data.get("imdbRating"),
                "poster": data.get("Poster") if data.get("Poster") != "N/A" else None
            }
        return None
    except Exception as e:
        return {"error": str(e)}

async def delete_later(message, seconds):
    await asyncio.sleep(seconds)
    try:
        await message.delete()
    except:
        pass

def build_keyboard(results, page, total_pages):
    start = (page - 1) * RESULTS_PER_PAGE
    end = start + RESULTS_PER_PAGE
    current = results[start:end]

    buttons = [
        [InlineKeyboardButton("📤 إرسال الكل", callback_data="sendall"),
         InlineKeyboardButton("📅 السنة", callback_data="year"),
         InlineKeyboardButton("🌐 اللغة", callback_data="lang")],
        [InlineKeyboardButton("📦 الجودة", callback_data="q"),
         InlineKeyboardButton("🎞️ الموسم", callback_data="season"),
         InlineKeyboardButton("🎬 الحلقات", callback_data="eps")]
    ]

    for video in current:
        video_id, title, file_id, quality, size = video
        label = f"{title} - {format_size(size)}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"play_{video_id}")])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"page_{page-1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"page_{page+1}"))
    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(buttons)

@app.on_message(filters.command("start"))
def start(client, msg):
    args = msg.text.split()
    if len(args) > 1 and args[1].startswith("video_"):
        video_id = int(args[1].split("_")[1])
        video = get_video_by_id(video_id)
        if video:
            title, file_id = video
            sent = client.send_video(msg.chat.id, file_id, caption=f"🎬 {title}")
            warning = client.send_message(msg.chat.id, "⚠️ يُفضّل تحويل الفيديو إلى الرسائل المحفوظة.")
            asyncio.create_task(delete_later(sent, 600))
            asyncio.create_task(delete_later(warning, 600))
        return

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 فيسبوك", url="https://www.facebook.com/profile.php?id=61557540113498"),
         InlineKeyboardButton("📸 انستغرام", url="https://www.instagram.com/cimaparadiso1988")],
        [InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/kinanalyousef")]
    ])
    msg.reply_photo(
        photo="https://i.imgur.com/tb1QHDy.jpg",
        caption="👋 أهلاً بك في منصة Cima Paradiso 🎬\nتابعنا لكل جديد 🎞️",
        reply_markup=buttons
    )

@app.on_message(filters.video & filters.chat(-1002636792002))
def save_video(_, msg):
    title = clean_title(msg.caption or msg.video.file_name or "غير معروف")
    file_id = msg.video.file_id
    size = msg.video.file_size
    match = re.search(r'(1080p|720p|480p|360p)', title)
    quality = match.group(1) if match else ""
    insert_video(title, file_id, quality, size)
    msg.reply("✅ تم حفظ الفيديو! 🎬")

@app.on_message(filters.text & filters.chat(-1002727731619))
def search(client, msg):
    query = clean_title(msg.text)
    results = search_videos(query)

    # تحقق من وجود from_user
    if not msg.from_user:
        reply = msg.reply("⚠️ لا يمكن تحديد هوية المرسل.")
        asyncio.create_task(delete_later(reply, 300))
        return

    user_id = msg.from_user.id
    username = f"@{msg.from_user.username}" if msg.from_user.username else "مستخدم مجهول"

    if not results:
        reply = msg.reply("❌ لا يوجد نتائج.")
        asyncio.create_task(delete_later(reply, 300))
        return

    info = get_movie_info(query)
    total_pages = math.ceil(len(results) / RESULTS_PER_PAGE)

    caption = (
        f"📽️ نتيجة البحث: {msg.text}\n"
        f"👤 الطلب من: {username}\n"
        f"⏱️ وقت الاستجابة: {time.time() - msg.date.timestamp():.2f} ثانية\n"
        "🧹 سيتم حذف هذه الرسالة بعد 5 دقائق"
    )

    search_cache[user_id] = {
        "query": query,
        "results": results,
        "poster": info["poster"] if info else None,
        "caption": caption
    }

    markup = build_keyboard(results, 1, total_pages)

    if info and info.get("poster"):
        sent = client.send_photo(chat_id=msg.chat.id, photo=info["poster"], caption=caption, reply_markup=markup)
    else:
        sent = msg.reply(caption, reply_markup=markup)

    asyncio.create_task(delete_later(sent, 300))

@app.on_callback_query()
def handle_callback(client, query):
    data = query.data
    user_id = query.from_user.id

    if data.startswith("page_"):
        page = int(data.split("_")[1])
        cache = search_cache.get(user_id)
        if cache:
            total_pages = math.ceil(len(cache["results"]) / RESULTS_PER_PAGE)
            markup = build_keyboard(cache["results"], page, total_pages)
            try:
                query.message.edit_reply_markup(markup)
                query.answer()
            except:
                pass

    elif data.startswith("play_"):
        video_id = int(data.split("_")[1])
        video = get_video_by_id(video_id)
        if video:
            title, file_id = video
            start_link = f"https://t.me/{client.me.username}?start=video_{video_id}"
            query.answer("📩 سيتم توجيهك للخاص...")
            query.message.reply(
                f"📥 لتحميل الفيديو:\n➡️ [اضغط هنا]({start_link})",
                disable_web_page_preview=True
            )

    elif data == "sendall":
        cache = search_cache.get(user_id)
        if cache:
            send_videos(cache["results"], user_id)
            query.answer("📤 تم الإرسال.")

def send_videos(results, user_id):
    for video in results:
        _, title, file_id, _, _ = video
        try:
            sent = app.send_video(user_id, file_id, caption=f"🎬 {title}")
            warn = app.send_message(user_id, "⚠️ يُفضّل تحويل الفيديو إلى الرسائل المحفوظة.")
            asyncio.create_task(delete_later(sent, 600))
            asyncio.create_task(delete_later(warn, 600))
        except:
            continue

app.run()