# 🤖 Telegram Earnings Bot (aiogram 3.x)

import asyncio
import logging
import os
import random
import sqlite3
import time
from contextlib import closing
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

# ============================ الإعدادات ============================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN غير موجود.")

POINTS_PER_DINAR = 100
WITHDRAW_MIN = 5000
AD_REWARD = 20
TASK_REWARD = 50
REFERRAL_REWARD = 100
DAILY_REWARD = 75
SPIN_COOLDOWN = 3600
DB_PATH = "bot.db"

SPIN_PRIZES = [10, 20, 50, 100, 0]

logging.basicConfig(level=logging.INFO)

# ============================ قاعدة البيانات ============================
def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def db_init():
    with closing(db_conn()) as c, c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            points INTEGER DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            last_spin INTEGER DEFAULT 0,
            last_daily INTEGER DEFAULT 0
        )
        """)

def get_user(user_id):
    with closing(db_conn()) as c:
        return c.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()

def add_user(user):
    with closing(db_conn()) as c, c:
        c.execute("INSERT OR IGNORE INTO users (user_id, full_name) VALUES (?,?)",
                  (user.id, user.full_name))

def add_points(user_id, pts):
    with closing(db_conn()) as c, c:
        c.execute("UPDATE users SET points = points + ? WHERE user_id=?", (pts, user_id))

# ============================ البوت ============================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎡 عجلة الحظ", callback_data="spin")],
        [InlineKeyboardButton(text="🎁 مكافأة يومية", callback_data="daily")],
        [InlineKeyboardButton(text="🏆 الترتيب", callback_data="top")],
    ])

@dp.message(CommandStart())
async def start(msg: Message):
    add_user(msg.from_user)
    await msg.answer("🚀 مرحبا بك في بوت الأرباح", reply_markup=main_menu())

@dp.callback_query(F.data == "spin")
async def spin(cb: CallbackQuery):
    user = get_user(cb.from_user.id)
    now = int(time.time())

    if now - user["last_spin"] < SPIN_COOLDOWN:
        await cb.answer("⏳ حاول لاحقاً", show_alert=True)
        return

    reward = random.choice(SPIN_PRIZES)
    add_points(user["user_id"], reward)

    with closing(db_conn()) as c, c:
        c.execute("UPDATE users SET last_spin=? WHERE user_id=?",
                  (now, user["user_id"]))

    await cb.message.answer(f"🎉 ربحت {reward} نقطة!")
    await cb.answer()

@dp.callback_query(F.data == "daily")
async def daily(cb: CallbackQuery):
    user = get_user(cb.from_user.id)
    now = int(time.time())

    if now - user["last_daily"] < 86400:
        await cb.answer("⏳ ارجع غداً", show_alert=True)
        return

    add_points(user["user_id"], DAILY_REWARD)

    with closing(db_conn()) as c, c:
        c.execute("UPDATE users SET last_daily=? WHERE user_id=?",
                  (now, user["user_id"]))

    await cb.message.answer(f"🎁 +{DAILY_REWARD} نقطة")
    await cb.answer()

@dp.callback_query(F.data == "top")
async def top(cb: CallbackQuery):
    with closing(db_conn()) as c:
        users = c.execute("SELECT * FROM users ORDER BY points DESC LIMIT 10").fetchall()

    text = "🏆 أفضل المستخدمين:\n\n"
    for i, u in enumerate(users, 1):
        text += f"{i}. {u['full_name']} - {u['points']} نقطة\n"

    await cb.message.answer(text)
    await cb.answer()

async def main():
    db_init()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
