import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from openai import OpenAI
import requests

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
RACING_USER = os.getenv("RACING_USER")
RACING_PASS = os.getenv("RACING_PASS")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler = AsyncIOScheduler(timezone="GMT")

def get_todays_racecards():
    if not RACING_USER or not RACING_PASS:
        return "No Racing API credentials found"
    try:
        url = "https://api.theracingapi.com/v1/racecards/free"
        response = requests.get(url, auth=(RACING_USER, RACING_PASS), timeout=15)
        if response.status_code == 200:
            data = response.json()
            cards = data.get("racecards", [])
            meetings = [card.get("course", "Unknown") for card in cards]
            return ", ".join(list(dict.fromkeys(meetings)))
        else:
            return f"API error ({response.status_code})"
    except Exception as e:
        return f"Fetch error: {str(e)[:80]}"

async def analyze_with_ai(meetings):
    try:
        client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
        date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')

        prompt = f"""You are a professional UK & Irish horse racing analyst.
Date: {date_today}
Today's real meetings: {meetings}

Give exactly 4 strong bets + 1 4-fold accumulator from today's races only.
Format: Time - Venue - Horse - Confidence (1-10) - Short reasoning."""

        response = client.chat.completions.create(
            model="grok-4.20-reasoning",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ AI Error: {str(e)[:200]}"

@bot.command(name="tips")
async def manual_tips(ctx):
    msg = await ctx.send("🐎 **RacingAI** – Fetching real racecards... ⏳")
    meetings = get_todays_racecards()
    analysis = await analyze_with_ai(meetings)
    
    embed = discord.Embed(
        title="🐎 RacingAI Tips",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')}\n🔥 Powered by xAI Grok",
        color=0x00ff88
    )
    embed.add_field(name="Today's Meetings", value=meetings, inline=False)
    embed.add_field(name="📌 4 Best Bets + 4-Fold Acca", value=analysis[:1020], inline=False)
    embed.set_footer(text="For entertainment only • Gamble responsibly • 18+")
    await msg.edit(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
