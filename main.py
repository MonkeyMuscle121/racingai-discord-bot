import os
from datetime import datetime
import discord
from discord.ext import commands
from dotenv import load_dotenv
import requests

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
RACING_USER = os.getenv("RACING_USER")
RACING_PASS = os.getenv("RACING_PASS")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.command(name="tips")
async def manual_tips(ctx):
    await ctx.send("🐎 Fetching real racecards from API...")

    try:
        url = "https://api.theracingapi.com/v1/racecards/free"
        response = requests.get(url, auth=(RACING_USER, RACING_PASS), timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            await ctx.send(f"✅ API Success! Found {len(data.get('racecards', []))} races today.")
            # Show first few meetings
            meetings = [c.get("course", "Unknown") for c in data.get("racecards", [])[:10]]
            await ctx.send("Today's Meetings: " + ", ".join(meetings))
        else:
            await ctx.send(f"❌ API Error: {response.status_code}")
    except Exception as e:
        await ctx.send(f"❌ Fetch failed: {str(e)[:100]}")

@bot.event
async def on_ready():
    print(f"✅ Bot is ONLINE!")

bot.run(DISCORD_TOKEN)
