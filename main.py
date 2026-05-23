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

# ====================== DISPLAY ======================
def format_tips_for_display(tips_list, is_specific=False):
    if not tips_list:
        return "No good tips found for this one."
    lines = []
    for i, tip in enumerate(tips_list, 1):
        day = tip.get("day", "")
        event = tip.get("event", "Unknown")
        selection = tip.get("selection", "Unknown")
        time = tip.get("time", "")
        comment = tip.get("comment", "This smells like money... 👀")
        
        day_str = f"**{day}** " if day else ""
        time_str = f" ⏰ {time}" if time else ""
        
        lines.append(
            f"**{i}.** {day_str}{event}{time_str}\n"
            f"**Pick:** {selection}\n"
            f"**Comment:** {comment}"
        )
    return "\n\n".join(lines)

# ====================== JSON EXTRACTOR ======================
def extract_json_from_text(text: str):
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start == -1:
            raise ValueError
        json_str = text[start:end]
        parsed = json.loads(json_str)
        return parsed.get("tips", []) if isinstance(parsed.get("tips"), list) else []
    except:
        return []

# ====================== GET TIPS (General or Specific) ======================
async def get_sports_tips(sport: str, specific_event: str = None):
    try:
        client = AsyncClient(api_key=XAI_API_KEY, timeout=85)
        chat = client.chat.create(
            model="grok-4.20-reasoning",
            tools=[web_search(), x_search()],
            temperature=0.75,
            max_turns=5,
        )
        
        now = datetime.now(pytz.timezone('Europe/London'))
        cutoff = (now + timedelta(hours=48)).strftime('%A %d %B %Y')
        
        if specific_event:
            prompt = f"""
CURRENT TIME: {now.strftime('%A %d %B %Y %H:%M BST')}
Focus ONLY on this specific event: **{specific_event}** in **{sport}**.

Reply with **VALID JSON ONLY**:
{{
  "tips": [
    {{"day": "Thursday", "event": "{specific_event}", "selection": "Pick", "time": "HH:MM", "comment": "Cheeky savage comment"}}
  ]
}}
Give exactly 3 tips.
"""
        else:
            prompt = f"""
CURRENT TIME: {now.strftime('%A %d %B %Y %H:%M BST')}
ONLY events from NOW until {cutoff}.
Focus ONLY on **{sport}**.

Reply with **VALID JSON ONLY** with exactly 4 tips.
"""
        
        chat.append(system("You are a savage, cheeky Racing AI bot. Be funny in comments. Reply with VALID JSON ONLY."))
        chat.append(user(prompt))
        response = await chat.sample()
        
        cleaned = clean_response(response.content)
        tips_list = extract_json_from_text(cleaned)
        return format_tips_for_display(tips_list, bool(specific_event)), tips_list
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return "❌ Failed to fetch tips.", []

# ====================== SAVE / LOAD ======================
def save_tips(sport: str, tips_list: list, specific_event=None):
    try:
        data = {}
        if TIPS_FILE.exists():
            with open(TIPS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        key = normalize_sport(sport) + (f"_{specific_event}" if specific_event else "")
        data[key] = {
            "timestamp": datetime.now(pytz.timezone('Europe/London')).isoformat(),
            "sport": sport,
            "event": specific_event,
            "tips": tips_list
        }
        
        with open(TIPS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Save failed: {e}")

# ====================== AUTO CHECKER (Same as before) ======================
async def check_individual_results(entry):
    try:
        client = AsyncClient(api_key=XAI_API_KEY, timeout=70)
        chat = client.chat.create(model="grok-4.20-reasoning", tools=[web_search(), x_search()], temperature=0.6, max_turns=6)
        
        current_time = datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M BST')
        
        prompt = f"""
CURRENT TIME: {current_time}

Check these tips for FINAL RESULTS:

{json.dumps(entry['tips'], indent=2)}

- ONLY mark finished events with ✅ **WON** or ❌ **LOST**
- Be savage and funny
"""
        chat.append(system("You are a savage Racing AI bot. Search real results."))
        chat.append(user(prompt))
        response = await chat.sample()
        return clean_response(response.content)
    except:
        return None

async def auto_check_tips():
    logger.info("🔄 V2.6 Auto Checker Running...")
    data = load_all_tips()
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: return

    for key, entry in list(data.items()):
        if not entry.get("tips"): continue
        result_text = await check_individual_results(entry)
        if result_text and any(x in result_text for x in ["✅", "❌", "WON", "LOST"]):
            title = f"🔄 AUTO RESULTS — {entry['sport'].title()}"
            if entry.get("event"):
                title += f" | {entry['event']}"
            embed = discord.Embed(title=title, description=f"📅 {entry['timestamp'][:16]}", color=0x00ff88)
            embed.add_field(name="Verdict", value=result_text[:3900], inline=False)
            embed.set_footer(text="✅ Won • ❌ Lost • Auto every 30 mins")
            await channel.send(embed=embed)

    cleanup_old_tips()

def load_all_tips():
    try:
        if not TIPS_FILE.exists(): return {}
        with open(TIPS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def cleanup_old_tips():
    try:
        data = load_all_tips()
        cutoff = datetime.now(pytz.timezone('Europe/London')) - timedelta(days=3)
        cleaned = {k: v for k, v in data.items() if datetime.fromisoformat(v["timestamp"]) > cutoff}
        with open(TIPS_FILE, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, indent=2)
    except:
        pass

# ====================== COMMANDS ======================
@bot.tree.command(name="tips", description="Get 4 general hot tips")
async def hot_tips(interaction: discord.Interaction, sport: str = "all"):
    await interaction.response.defer(thinking=True)
    display_name = "All Sports" if sport.lower() == "all" else sport.replace("_", " ").title()
    status_msg = await interaction.followup.send(get_random_loading_message())
    
    nice_display, tips_list = await get_sports_tips(sport)
    save_tips(sport, tips_list)

    embed = discord.Embed(title=f"🔥 Top 4 {display_name} Hot Tips", description=f"📅 {datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M')} BST", color=0xff00ff)
    embed.add_field(name="Tips", value=nice_display, inline=False)
    embed.set_footer(text="🔥 For entertainment only • Not real betting advice • Gamble responsibly • 18+")
    await interaction.followup.send(embed=embed)
    try: await status_msg.delete()
    except: pass

@bot.tree.command(name="tipsevent", description="Get 3 tips for a specific match/fight")
async def tips_event(interaction: discord.Interaction, sport: str, event: str):
    await interaction.response.defer(thinking=True)
    status_msg = await interaction.followup.send(get_random_loading_message())
    
    nice_display, tips_list = await get_sports_tips(sport, event)
    save_tips(sport, tips_list, event)

    embed = discord.Embed(
        title=f"🎯 3 Tips for {event}",
        description=f"📅 {datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M')} BST",
        color=0xff00ff
    )
    embed.add_field(name="Tips", value=nice_display, inline=False)
    embed.set_footer(text="🔥 For entertainment only • Not real betting advice • Gamble responsibly • 18+")

    await interaction.followup.send(embed=embed)
    try: await status_msg.delete()
    except: pass

@bot.event
async def on_ready():
    print(f"✅ {bot.user} V2.6 — SPECIFIC EVENT MODE UNLOCKED!")
    await bot.tree.sync()
    scheduler.start()
    scheduler.add_job(auto_check_tips, 'interval', minutes=30, next_run_time=datetime.now(pytz.timezone('Europe/London')))
    print("✅ Auto checker active")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
