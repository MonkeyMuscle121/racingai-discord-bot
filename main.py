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

def get_raw_race_data():
    try:
        url = "https://api.theracingapi.com/v1/racecards/free"
        response = requests.get(url, auth=(RACING_USER, RACING_PASS), timeout=15)
        if response.status_code == 200:
            data = response.json()
            cards = data.get("racecards", [])
            summary = []
            for card in cards[:20]:
                time = card.get("time", "??:??")
                course = card.get("course", "Unknown")
                summary.append(f"{time} {course}")
            return "\n".join(summary)
        else:
            return f"API Error: {response.status_code}"
    except Exception as e:
        return f"Fetch failed: {str(e)[:100]}"

@bot.command(name="tips")
async def manual_tips(ctx):
    msg = await ctx.send("🐎 Fetching real race data... ⏳")
    
    raw_data = get_raw_race_data()
    await ctx.send(f"**Raw Data from Racing API:**\n```{raw_data[:1500]}```")
    
    # For now, just show raw data so we can see what's wrong
    embed = discord.Embed(
        title="🐎 RacingAI Diagnostic",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')}",
        color=0x00ff88
    )
    embed.add_field(name="Today's Real Meetings & Times", value=raw_data[:1000] or "No data", inline=False)
    await msg.edit(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
