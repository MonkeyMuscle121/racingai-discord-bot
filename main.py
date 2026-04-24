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

async def get_sports_tips(sport: str):
    try:
        normalized = normalize_sport(sport)
        
        client = AsyncClient(api_key=XAI_API_KEY, timeout=110)
        
        chat = client.chat.create(
            model="grok-4.20-reasoning",
            tools=[web_search(), x_search()],
            temperature=0.85,
            max_turns=6,          # Extra room for accurate scheduling
        )

        date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')
        
        if normalized == "bangers":
            sport_display = "Bangers 🔥"
            extra = "Only return high confidence bangers (80%+)."
        else:
            sport_display = "All Sports" if normalized == "all" else ("Horse Racing" if normalized == "horse_racing" else sport.replace("_", " ").title())
            extra = ""

        prompt = f"""
Current exact date & time: {date_today} BST.

You MUST include accurate date + time for every event (e.g. "Fri 24 Apr - 15:30 BST" or "Sat 25 Apr - 20:00 BST").

Analyse within the next 48 hours focusing mainly on **{sport}**.
{extra}

Return exactly the top 4 hot tips in this format (keep it tight):

**Top 4 {sport_display}...**

1. **Event** – Specific bet (exact teams/fighters/horses, odds if available, **Date + precise time in BST**)  
   → Then one savage, funny, cheeky bantery one-liner.

Use mum, dad, nan, grandad, sister, brother jokes and general humour. Swearing is fine.
"""

        chat.append(system("""You are a proper savage, cheeky Racing AI bot. 
Always include exact date + BST time for every event. Use heavy banter, swearing, family jokes. 
Keep it very funny but never tell anyone to bet their house or mortgage."""))
        
        chat.append(user(prompt))

        response = await chat.sample()
        cleaned = clean_response(response.content)
        return cleaned or "No tips available."

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return f"❌ Error fetching tips: {str(e)[:200]}"

# ====================== SLASH COMMAND ======================
@bot.tree.command(name="tips", description="Get hot tips - e.g. /tips football, /tips horse, /tips bangers")
async def hot_tips(interaction: discord.Interaction, sport: str = "all"):
    await interaction.response.defer(thinking=True)
    
    normalized = normalize_sport(sport)
    
    if normalized == "bangers":
        display_name = "Bangers 🔥"
    else:
        display_name = "All Sports" if normalized == "all" else ("Horse Racing" if normalized == "horse_racing" else sport.replace("_", " ").title())
    
    status_msg = await interaction.followup.send(
        "🔍 Analysing real-time data... **This can take approx 60 seconds** due to live searches.\n"
        "So stop ya whining 😂 and go and buy a monkey or some gainz while you wait — awesome shit like this don't come for free!"
    )

    analysis = await get_sports_tips(sport)
    
    embed = discord.Embed(
        title=f"🔥 Top 4 {display_name}",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y %H:%M')} BST",
        color=0xff00ff
    )
    
    if len(analysis) > 1000:
        chunks = [analysis[i:i+1000] for i in range(0, len(analysis), 1000)]
        for chunk in chunks:
            embed.add_field(name="", value=chunk, inline=False)
    else:
        embed.add_field(name="Hot Tips", value=analysis or "No data at the moment.", inline=False)
    
    embed.set_footer(text="🔥 For entertainment only • Not real betting advice • Gamble responsibly • 18+ • Bet at your own risk")
    
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
