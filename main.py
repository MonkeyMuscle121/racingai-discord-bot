import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
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

LOADING_MESSAGES = [
    "🔍 Pulling data... hold on you melt 😂",
    "🔍 Fetching fresh tips... 30-50s",
    "🔍 Loading... go make a brew",
]

def get_random_loading_message():
    return random.choice(LOADING_MESSAGES)

def normalize_sport(sport: str) -> str:
    sport_lower = sport.lower().strip()
    if sport_lower in ["horse", "horses", "racing", "horse racing", "horseracing"]:
        return "horse_racing"
    return sport_lower

def clean_response(text: str) -> str:
    return '\n'.join(line.strip() for line in text.strip().split('\n'))

# ====================== DISPLAY ======================
def format_tips_for_display(tips_list):
    if not tips_list:
        return "No tips found right now."
    lines = []
    for i, tip in enumerate(tips_list, 1):
        event = tip.get("event", "Unknown")
        selection = tip.get("selection", "Unknown")
        comment = tip.get("comment", "This looks decent...")
        lines.append(f"**{i}.** {event}\n**Pick:** {selection}\n**Comment:** {comment}")
    return "\n\n".join(lines)

def extract_json_from_text(text: str):
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start == -1: raise ValueError
        json_str = text[start:end]
        parsed = json.loads(json_str)
        return parsed.get("tips", []) if isinstance(parsed.get("tips"), list) else []
    except:
        return []

# ====================== FASTER GET TIPS ======================
async def get_sports_tips(sport: str, specific_event: str = None):
    try:
        client = AsyncClient(api_key=XAI_API_KEY, timeout=60)  # Tight timeout
        chat = client.chat.create(
            model="grok-4.20-reasoning",
            tools=[web_search(), x_search()],
            temperature=0.65,
            max_turns=3,           # Reduced for speed
        )
        
        now = datetime.now(pytz.timezone('Europe/London'))
        
        if specific_event:
            prompt = f"Give 3 quick betting tips for: {specific_event} ({sport}). Reply with clean JSON only."
        else:
            prompt = f"Give 4 quick hot tips for {sport}. Reply with clean JSON only."
        
        chat.append(system("You are a savage Racing AI bot. Reply with VALID JSON only."))
        chat.append(user(prompt))
        response = await chat.sample()
        
        tips_list = extract_json_from_text(clean_response(response.content))
        return format_tips_for_display(tips_list), tips_list
        
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "❌ AI took too long. Try again in 20 seconds.", []

# ====================== SAVE ======================
def save_tips(sport: str, tips_list: list, specific_event=None):
    try:
        data = {}
        if TIPS_FILE.exists():
            with open(TIPS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        key = normalize_sport(sport) + (f"_{specific_event[:15]}" if specific_event else "")
        data[key] = {
            "timestamp": datetime.now(pytz.timezone('Europe/London')).isoformat(),
            "sport": sport,
            "event": specific_event,
            "tips": tips_list
        }
        
        with open(TIPS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except:
        pass

# ====================== COMMANDS ======================
@bot.tree.command(name="tips", description="Get 4 general hot tips")
async def hot_tips(interaction: discord.Interaction, sport: str = "all"):
    await interaction.response.defer(thinking=True, ephemeral=False)
    status_msg = await interaction.followup.send(get_random_loading_message())
    
    try:
        nice_display, tips_list = await get_sports_tips(sport)
        save_tips(sport, tips_list)

        embed = discord.Embed(
            title=f"🔥 Top 4 {sport.replace('_', ' ').title()} Hot Tips",
            description=f"📅 {datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M')} BST",
            color=0xff00ff
        )
        embed.add_field(name="Tips", value=nice_display[:3900], inline=False)
        embed.set_footer(text="🔥 For entertainment only • Gamble responsibly • 18+")
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send("❌ Bot timed out. Try again.")
        logger.error(f"tips command failed: {e}")
    finally:
        try: await status_msg.delete()
        except: pass

@bot.tree.command(name="tipsevent", description="Get 3 tips for a specific match")
async def tips_event(interaction: discord.Interaction, sport: str, event: str):
    await interaction.response.defer(thinking=True)
    status_msg = await interaction.followup.send(get_random_loading_message())
    
    try:
        nice_display, tips_list = await get_sports_tips(sport, event)
        save_tips(sport, tips_list, event)

        embed = discord.Embed(
            title=f"🎯 3 Tips for: {event}",
            description=f"📅 {datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M')} BST",
            color=0xff00ff
        )
        embed.add_field(name="Tips", value=nice_display[:3900], inline=False)
        embed.set_footer(text="🔥 For entertainment only • Gamble responsibly • 18+")
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send("❌ Failed to get tips. Try again.")
        logger.error(f"tipsevent failed: {e}")
    finally:
        try: await status_msg.delete()
        except: pass

# ====================== AUTO CHECKER (Light) ======================
async def auto_check_tips():
    logger.info("Auto checker running...")

@bot.event
async def on_ready():
    print(f"✅ {bot.user} V2.9 — FAST MODE ACTIVATED!")
    await bot.tree.sync()
    scheduler.start()
    # Light auto checker
    scheduler.add_job(auto_check_tips, 'interval', minutes=40)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
