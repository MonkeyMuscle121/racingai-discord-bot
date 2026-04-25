import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
import re
import random

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

# Brutal loading messages
LOADING_MESSAGES = [
    "🔍 Pulling live data... 50-80 seconds. Go make a brew you impatient cunt 😂",
    "🔍 Analysing real-time... This takes 50-80s. Go piss or buy some $GAINZ",
    "🔍 Fetching fresh tips... 50-80 seconds. Stop crying",
    "🔍 Live data loading... Go touch grass you melt",
]

def get_random_loading_message():
    return random.choice(LOADING_MESSAGES)

def normalize_sport(sport: str) -> str:
    sport_lower = sport.lower().strip()
    if sport_lower in ["horse", "horses", "racing", "horse racing", "horseracing"]:
        return "horse_racing"
    return sport_lower

def clean_response(text: str) -> str:
    text = re.sub(r'\n{3,}', '\n\n', text.strip())
    return '\n'.join(line.strip() for line in text.split('\n'))

async def get_sports_tips(sport: str):
    try:
        client = AsyncClient(api_key=XAI_API_KEY, timeout=110)
        
        chat = client.chat.create(
            model="grok-4.20-reasoning",
            tools=[web_search(), x_search()],
            temperature=0.8,
            max_turns=6,
        )

        now = datetime.now(pytz.timezone('GMT'))
        current_time_str = now.strftime('%A %d %B %Y %H:%M BST')
        cutoff = (now + timedelta(hours=48)).strftime('%A %d %B %Y')

        sport_display = "Horse Racing" if normalize_sport(sport) == "horse_racing" else sport.replace("_", " ").title()

        prompt = f"""
CURRENT TIME: {current_time_str}

STRICT 48 HOUR RULE: ONLY events in the next 48 hours.

Focus ONLY on **{sport}**.

For horse racing: ONLY use real current runners from actual meetings. Do not invent horses that are not declared.

Return exactly 4 tips in this format:

**1. Event** – Bet (odds) | **Date + Time BST** | Confidence: XX%  
→ Savage funny bantery line.
"""

        if normalize_sport(sport) in ["all", "mixed", "general"]:
            prompt = prompt.replace("Focus ONLY on **all**", "UFC, boxing, darts, horse racing, and football")

        chat.append(system("""You are a savage, cheeky Racing AI bot. 
For horse racing you MUST only use real declared runners from current meetings. 
Always include accurate Date + Time BST and Confidence %. Keep it funny."""))
        
        chat.append(user(prompt))

        response = await chat.sample()
        cleaned = clean_response(response.content)
        return cleaned or "No upcoming events in next 48 hours."

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return f"❌ Error fetching tips: {str(e)[:200]}"

# ====================== SLASH COMMAND ======================
@bot.tree.command(name="tips", description="Get hot tips - e.g. /tips football, /tips horse, /tips boxing")
async def hot_tips(interaction: discord.Interaction, sport: str = "all"):
    await interaction.response.defer(thinking=True)
   
    normalized = normalize_sport(sport)
    display_name = "All Sports" if normalized == "all" else ("Horse Racing" if normalized == "horse_racing" else sport.replace("_", " ").title())
   
    status_msg = await interaction.followup.send(get_random_loading_message())
    
    analysis = await get_sports_tips(sport)
   
    embed = discord.Embed(
        title=f"🔥 Top 4 {display_name} Hot Tips",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y %H:%M')} BST",
        color=0xff00ff
    )
   
    embed.add_field(name="Hot Tips", value=analysis[:3900] or "No upcoming events in next 48 hours.", inline=False)
   
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
