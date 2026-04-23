import os
from datetime import datetime, timedelta
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
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler = AsyncIOScheduler(timezone="GMT")

def get_upcoming_events():
    try:
        # Free public API for upcoming events
        today = datetime.now(pytz.utc).strftime('%Y-%m-%d')
        response = requests.get(f"https://www.thesportsdb.com/api/v1/json/3/eventsday.php?d={today}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            events = data.get("events", [])[:15]
            summary = []
            for e in events:
                sport = e.get("strSport", "Sport")
                event = e.get("strEvent", "Event")
                time = e.get("strTime", "TBD")
                summary.append(f"{sport} - {event} ({time})")
            return "\n".join(summary) if summary else "Popular events in next 48 hours"
    except:
        pass
    return "Horse Racing, Premier League, Tennis, UFC, Darts (popular events in next 48 hours)"

async def get_daily_tips():
    try:
        client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
        date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')

        events = get_upcoming_events()

        prompt = f"""Sharp multi-sport tipster.
Current date: {date_today}.

Upcoming events in next 48 hours: {events}

Give exactly 4 strong bets from real events happening soon.

For each bet include:
- Sport & Event (with time/date)
- Pick
- Confidence (1-10)
- Short reasoning"""

        response = client.chat.completions.create(
            model="grok-4.20-reasoning",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)[:150]}"

@bot.command(name="tips")
async def daily_tips(ctx):
    msg = await ctx.send("🔥 **Multi-Sport Tips** – Finding real events in next 48 hours... ⏳")
    analysis = await get_daily_tips()
    
    embed = discord.Embed(
        title="🔥 Multi-Sport Daily Tips",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')}\nPowered by xAI Grok",
        color=0xff00ff
    )
    embed.add_field(name="📌 4 Strong Bets (Next 48 Hours)", value=analysis[:1020], inline=False)
    embed.set_footer(text="For entertainment only • Gamble responsibly • 18+")
    await msg.edit(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
