import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import logging
import re
# xAI SDK
from xai_sdk import AsyncClient
from xai_sdk.chat import user, system
from xai_sdk.tools import web_search, x_search

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler(timezone="GMT")

def normalize_sport(sport: str) -> str:
    sport_lower = sport.lower().strip()
    if sport_lower in ["horse", "horses", "racing", "horse racing", "horseracing"]:
        return "horse_racing"
    return sport_lower

def clean_response(text: str) -> str:
    text = re.sub(r'\n{3,}', '\n\n', text.strip())
    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join(lines)

# ====================== FASTER CHEEKY BANTER TIPS ======================
async def get_sports_tips(sport: str):
    try:
        normalized = normalize_sport(sport)
       
        client = AsyncClient(api_key=XAI_API_KEY, timeout=90)  # Reduced timeout
        
        chat = client.chat.create(
            model="grok-4",           # Fast & capable
            tools=[web_search(), x_search()],
            temperature=0.88,
            max_turns=3,              # ← Big speed boost
        )
        
        date_today = datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y')
       
        sport_display = "Horse Racing" if normalized == "horse_racing" else sport.replace("_", " ").title()
       
        prompt = f"""
Current date: {date_today}. Use BST times.

Give me the **top 4 hot tips right now** for {sport}.

Format exactly like this:

**Top 4 {sport_display} Hot Tips...**

1. **Event** – Specific bet (horses/teams/fighters, odds if known, **exact BST time**)
   → Cheeky funny one-liner with mum/dad/nan banter.

Keep each tip short and punchy. Light swearing ok. Fun British banter only.
"""

        if normalized in ["all", "mixed", "general"]:
            prompt = prompt.replace("for {sport}", "for UFC, boxing, darts, horse racing & football")

        chat.append(system("""You are a cheeky, savage British sports banter bot.
Funny mum/dad/nan/grandad jokes. Light-hearted wind-ups. Keep responses fast and entertaining."""))

        chat.append(user(prompt))
        response = await chat.sample()
        
        cleaned = clean_response(response.content)
        return cleaned or "No tips right now mate."

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return f"❌ Couldn't fetch tips: {str(e)[:100]}"

# ====================== SLASH COMMAND ======================
@bot.tree.command(name="tips", description="Get hot tips - e.g. /tips football, /tips horse, /tips boxing")
async def hot_tips(interaction: discord.Interaction, sport: str = "all"):
    await interaction.response.defer(thinking=True)
   
    normalized = normalize_sport(sport)
    display_name = "All Sports" if normalized == "all" else ("Horse Racing" if normalized == "horse_racing" else sport.replace("_", " ").title())
   
    status_msg = await interaction.followup.send(
        "🔍 Pulling fresh data... **Should be quicker this time** (30-45 seconds)\n"
        "Hold tight ya legend 😂"
    )
    
    analysis = await get_sports_tips(sport)
   
    embed = discord.Embed(
        title=f"🔥 Top 4 {display_name} Banter Tips",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y %H:%M')} BST",
        color=0xff00ff
    )
   
    if len(analysis) > 1000:
        chunks = [analysis[i:i+1000] for i in range(0, len(analysis), 1000)]
        for chunk in chunks:
            embed.add_field(name="", value=chunk, inline=False)
    else:
        embed.add_field(name="Hot Tips", value=analysis or "No data at the moment.", inline=False)
   
    embed.set_footer(text="🔥 For entertainment only • Gamble responsibly • 18+")
   
    await interaction.followup.send(embed=embed)
   
    try:
        await status_msg.delete()
    except:
        pass

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    try:
        await bot.tree.sync()
        print("✅ Slash commands synced")
    except Exception as e:
        print(f"Sync warning: {e}")
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
