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
import json
from pathlib import Path

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
scheduler = AsyncIOScheduler(timezone="Europe/London")

TIPS_FILE = Path("tips_history.json")
TIPS_FILE.touch(exist_ok=True)

# Brutal loading messages
LOADING_MESSAGES = [
    "🔍 Pulling live data... 40-65 seconds. Go make a brew you impatient cunt 😂",
    "🔍 Analysing real-time... This takes 40-65s. Go piss or buy some $GAINZ",
    "🔍 Fetching fresh tips... 40-65 seconds. Stop crying",
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

def save_tips(sport: str, tips_text: str):
    try:
        data = {}
        if TIPS_FILE.exists():
            with open(TIPS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        key = normalize_sport(sport)
        data[key] = {
            "timestamp": datetime.now(pytz.timezone('Europe/London')).isoformat(),
            "sport": sport,
            "tips": tips_text
        }
        
        with open(TIPS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save tips: {e}")

def load_latest_tips(sport: str = None):
    try:
        if not TIPS_FILE.exists():
            return None
        with open(TIPS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if sport:
            key = normalize_sport(sport)
            return data.get(key)
        else:
            # Return most recent
            return max(data.values(), key=lambda x: x.get("timestamp", ""))
    except:
        return None

async def check_tip_results(tips_data):
    if not tips_data:
        return None
    
    try:
        client = AsyncClient(api_key=XAI_API_KEY, timeout=70)
        chat = client.chat.create(
            model="grok-4.20-reasoning",
            tools=[web_search(), x_search()],
            temperature=0.6,
            max_turns=6,
        )
        
        current_time = datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M BST')
        
        prompt = f"""
CURRENT TIME: {current_time}
Here are the tips to check:

{tips_data['tips']}

Rules:
- ONLY check events that have already finished.
- For each tip: Mark with ✅ WON or ❌ LOST
- Be savage, funny and brutally honest.
- Ignore events still in progress.
Return clean formatted list with emojis.
"""
        chat.append(system("You are a savage Racing AI bot. Roast the losers, celebrate the winners."))
        chat.append(user(prompt))
        response = await chat.sample()
        return clean_response(response.content)
    except Exception as e:
        logger.error(f"Checker error: {e}")
        return None

# ====================== AUTO CHECKER TASK ======================
async def auto_check_all_tips():
    logger.info("Running auto tip checker...")
    try:
        if not TIPS_FILE.exists():
            return
            
        with open(TIPS_FILE, "r", encoding="utf-8") as f:
            all_tips = json.load(f)
        
        for key, tips_data in list(all_tips.items()):
            result = await check_tip_results(tips_data)
            if result:
                channel = bot.get_channel(CHANNEL_ID)
                if channel:
                    embed = discord.Embed(
                        title="🔄 AUTO TIP RESULTS",
                        description=f"**{tips_data['sport'].title()}** tips from {tips_data['timestamp'][:16]}",
                        color=0x00ff88
                    )
                    embed.add_field(name="Verdict", value=result[:3900], inline=False)
                    embed.set_footer(text="Auto-checked • Green = Bag secured • Red = Oof")
                    await channel.send(embed=embed)
                    logger.info(f"Posted auto results for {key}")
    except Exception as e:
        logger.error(f"Auto checker failed: {e}")

# ====================== GET TIPS ======================
async def get_sports_tips(sport: str):
    try:
        client = AsyncClient(api_key=XAI_API_KEY, timeout=75)
        chat = client.chat.create(
            model="grok-4.20-reasoning",
            tools=[web_search(), x_search()],
            temperature=0.75,
            max_turns=4,
        )
        
        now = datetime.now(pytz.timezone('Europe/London'))
        current_time_str = now.strftime('%A %d %B %Y %H:%M BST')
        cutoff = (now + timedelta(hours=48)).strftime('%A %d %B %Y')
        sport_display = "Horse Racing" if normalize_sport(sport) == "horse_racing" else sport.replace("_", " ").title()
        
        prompt = f"""
CURRENT EXACT TIME: {current_time_str}
STRICT 48 HOUR RULE: ONLY events starting from NOW until {cutoff}. No past events.
Focus ONLY on **{sport}**.
For horse racing: Use real declared runners only.
Return exactly 4 tips.
"""
        chat.append(system("You are a savage, cheeky Racing AI bot. Be fast and funny."))
        chat.append(user(prompt))
        response = await chat.sample()
        return clean_response(response.content) or "No upcoming events in next 48 hours."
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return f"❌ Error fetching tips: {str(e)[:200]}"

# ====================== SLASH COMMANDS ======================
@bot.tree.command(name="tips", description="Get hot tips - e.g. /tips football, /tips horse, /tips boxing")
async def hot_tips(interaction: discord.Interaction, sport: str = "all"):
    await interaction.response.defer(thinking=True)
 
    normalized = normalize_sport(sport)
    display_name = "All Sports" if normalized == "all" else ("Horse Racing" if normalized == "horse_racing" else sport.replace("_", " ").title())
 
    status_msg = await interaction.followup.send(get_random_loading_message())
  
    analysis = await get_sports_tips(sport)
    
    # SAVE FOR AUTO CHECKER
    save_tips(sport, analysis)

    embed = discord.Embed(
        title=f"🔥 Top 4 {display_name} Hot Tips",
        description=f"📅 {datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M')} BST",
        color=0xff00ff
    )
 
    embed.add_field(name="Hot Tips", value=analysis[:3900] or "No upcoming events in next 48 hours.", inline=False)
    embed.set_footer(text="🔥 Tips saved • Auto results every 2 hours • Gamble responsibly")

    await interaction.followup.send(embed=embed)
 
    try:
        await status_msg.delete()
    except:
        pass

# ====================== BOT EVENTS ======================
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE and READY TO PRINT!")
    try:
        await bot.tree.sync()
        print("✅ Slash commands synced")
    except Exception as e:
        print(f"Sync warning: {e}")
    
    # Start scheduler
    scheduler.start()
    
    # Auto check every 2 hours
    scheduler.add_job(auto_check_all_tips, 'interval', hours=2, next_run_time=datetime.now(pytz.timezone('Europe/London')))
    
    # Optional: Daily cleanup of old tips (older than 5 days)
    # scheduler.add_job(clean_old_tips, 'interval', hours=24)

print("🚀 Racing AI Bot with AUTO tip checker loaded!")
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
