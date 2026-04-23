import os
import asyncio
from datetime import datetime
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import requests
from openai import OpenAI   # We use OpenAI client for xAI compatibility

load_dotenv()

# ===================== CONFIG =====================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")          # NEW
RACING_USER = os.getenv("RACING_USER")
RACING_PASS = os.getenv("RACING_PASS")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler = AsyncIOScheduler(timezone="GMT")

# =============== DATA & WEATHER (unchanged) ===============
def get_todays_racecards():
    url = "https://api.theracingapi.com/v1/racecards/free"
    try:
        response = requests.get(url, auth=(RACING_USER, RACING_PASS), timeout=15)
        if response.status_code == 200:
            data = response.json()
            return data.get("racecards", [])
        else:
            print(f"API returned {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching racecards: {e}")
        return []

def get_weather(venue):
    courses = {
        "Newmarket": (52.24, 0.41), "Ascot": (51.41, -0.68), "Goodwood": (50.86, -0.76),
        "York": (53.96, -1.08), "Doncaster": (53.52, -1.13), "Chester": (53.19, -2.89),
        "Gowran Park": (52.67, -7.12), "Curragh": (53.13, -6.93), "Leopardstown": (53.27, -6.18),
        "Sandown": (51.38, -0.36), "Aintree": (53.48, -2.94), "Cheltenham": (51.92, -2.07)
    }
    if venue not in courses:
        return "Weather N/A"
    lat, lon = courses[venue]
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,precipitation&timezone=GMT"
        data = requests.get(url, timeout=10).json()
        temp = data['hourly']['temperature_2m'][12]
        rain = data['hourly']['precipitation'][12]
        return f"🌡️ {temp}°C | 🌧️ {rain}mm"
    except:
        return "Weather N/A"

# =============== AI ANALYSIS with xAI Grok ===============
async def analyze_with_ai(racecards):
    if not racecards:
        return "No race data available today."

    client = OpenAI(
        api_key=XAI_API_KEY,
        base_url="https://api.x.ai/v1"
    )
    
    race_summary = str(racecards[:15])

    prompt = f"""You are a professional UK & Irish horse racing analyst.
Date: {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')}

Today's race data summary:
{race_summary}

Task:
- Select exactly 4 strong bets (win or each-way recommended)
- Create 1 solid 4-fold accumulator
- For every selection include: Race time + venue, Horse name, Bet type, Confidence (1-10), short clear reasoning, estimated fair odds

Be realistic and honest. Use emojis for nice formatting.
Reply in clean, readable text only."""

    try:
        response = client.chat.completions.create(
            model="grok-4.1-fast-reasoning",   # Cost-effective & fast. Change to "grok-4.20-reasoning" later if you want maximum quality
            messages=[{"role": "user", "content": prompt}],
            temperature=0.65,
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"xAI API error: {e}")
        return "AI analysis temporarily unavailable. Please check API key and credits."

# =============== DAILY POST ===============
async def daily_racing_post():
    if CHANNEL_ID == 0:
        return
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return
    await channel.send("🐎 **RacingAI Daily Tips** – 10:00 GMT\nFetching today's cards... ⏳")
    racecards = get_todays_racecards()
    if not racecards:
        await channel.send("⚠️ No racing data available today.")
        return
    for card in racecards:
        card["weather"] = get_weather(card.get("course", ""))
    analysis = await analyze_with_ai(racecards)
    embed = discord.Embed(
        title="🐎 RacingAI Daily Tips",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')}\n🔥 Powered by xAI Grok",
        color=0x00ff88,
        timestamp=datetime.now(pytz.utc)
    )
    embed.add_field(name="📌 4 Best Bets + 4-Fold Acca", value=analysis[:4096], inline=False)
    embed.set_footer(text="For entertainment only • Gamble responsibly • 18+")
    await channel.send(embed=embed)

# =============== SCHEDULER ===============
@scheduler.scheduled_job('cron', hour=10, minute=0, timezone='GMT')
async def scheduled_job():
    await daily_racing_post()

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online using xAI Grok API!")
    scheduler.start()

# =============== START ===============
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
