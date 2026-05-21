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

# ====================== NICE DISPLAY ======================
def format_tips_for_display(tips_list):
    if not tips_list:
        return "No upcoming events found in the next 48 hours."
    lines = []
    for i, tip in enumerate(tips_list, 1):
        event = tip.get("event", "Unknown Event")
        selection = tip.get("selection", "Unknown")
        time = tip.get("time", "")
        time_str = f" ⏰ {time}" if time else ""
        lines.append(f"**{i}.** {event}{time_str}\n**Pick:** {selection}")
    return "\n\n".join(lines)

# ====================== ROBUST JSON EXTRACTOR ======================
def extract_json_from_text(text: str):
    try:
        # Find JSON block
        start = text.find('{')
        end = text.rfind('}') + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON found")
        
        json_str = text[start:end]
        parsed = json.loads(json_str)
        
        # Handle different possible structures
        if isinstance(parsed.get("tips"), list):
            return parsed["tips"]
        elif isinstance(parsed, list):
            return parsed
        return []
    except:
        # Fallback: Try to parse line by line if AI ignored JSON
        tips = []
        lines = text.split('\n')
        current_tip = {}
        for line in lines:
            if "event" in line.lower() or "vs" in line or "race" in line.lower():
                current_tip = {"event": line.strip(), "selection": "", "time": ""}
            elif "pick" in line.lower() or "selection" in line.lower():
                current_tip["selection"] = line.split(":", 1)[-1].strip() if ":" in line else line.strip()
                if current_tip.get("event"):
                    tips.append(current_tip.copy())
        return tips

# ====================== GET TIPS ======================
async def get_sports_tips(sport: str):
    try:
        client = AsyncClient(api_key=XAI_API_KEY, timeout=80)
        chat = client.chat.create(
            model="grok-4.20-reasoning",
            tools=[web_search(), x_search()],
            temperature=0.65,
            max_turns=5,
        )
        
        now = datetime.now(pytz.timezone('Europe/London'))
        cutoff = (now + timedelta(hours=48)).strftime('%A %d %B %Y')
        
        prompt = f"""
CURRENT TIME: {now.strftime('%A %d %B %Y %H:%M BST')}
ONLY events from NOW until {cutoff}.
Focus ONLY on **{sport}**.

**YOU MUST REPLY WITH VALID JSON ONLY. NO EXTRA TEXT.**

{{
  "tips": [
    {{"event": "Event name", "selection": "Your pick", "time": "HH:MM"}},
    ...
  ]
}}
Exactly 4 tips.
"""
        chat.append(system("You are a savage Racing AI bot. Reply with **VALID JSON ONLY**. No explanations, no markdown, no extra words."))
        chat.append(user(prompt))
        response = await chat.sample()
        
        cleaned = clean_response(response.content)
        tips_list = extract_json_from_text(cleaned)
        
        display_text = format_tips_for_display(tips_list)
        return display_text, tips_list
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"❌ Error fetching tips: {str(e)[:150]}", []

# ====================== SAVE / LOAD ======================
def save_tips(sport: str, tips_list: list):
    try:
        data = {}
        if TIPS_FILE.exists():
            with open(TIPS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        key = normalize_sport(sport)
        data[key] = {
            "timestamp": datetime.now(pytz.timezone('Europe/London')).isoformat(),
            "sport": sport,
            "tips": tips_list
        }
        
        with open(TIPS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Save failed: {e}")

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

# ====================== AUTO CHECKER ======================
async def auto_check_tips():
    logger.info("🔄 V2.2 Auto Checker Running...")
    data = load_all_tips()
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: return

    for key, entry in list(data.items()):
        if not entry.get("tips"): continue
        result_text = await check_individual_results(entry)
        if result_text:
            embed = discord.Embed(
                title=f"🔄 AUTO RESULTS — {entry['sport'].title()}",
                description=f"📅 {entry['timestamp'][:16]}",
                color=0x00ff88
            )
            embed.add_field(name="Verdict", value=result_text[:3900], inline=False)
            embed.set_footer(text="✅ Won • ❌ Lost • Auto every 30 mins")
            await channel.send(embed=embed)

    cleanup_old_tips()

async def check_individual_results(entry):
    try:
        client = AsyncClient(api_key=XAI_API_KEY, timeout=60)
        chat = client.chat.create(model="grok-4.20-reasoning", tools=[web_search(), x_search()], temperature=0.6)
        
        prompt = f"Current time: {datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M BST')}\n\nTips:\n{json.dumps(entry['tips'], indent=2)}\n\nMark each with ✅ WON or ❌ LOST if finished. Be savage."
        chat.append(system("You are a savage Racing AI bot."))
        chat.append(user(prompt))
        response = await chat.sample()
        return clean_response(response.content)
    except:
        return "Checker busy, try again soon."

# ====================== COMMAND ======================
@bot.tree.command(name="tips", description="Get hot tips")
async def hot_tips(interaction: discord.Interaction, sport: str = "all"):
    await interaction.response.defer(thinking=True)
    
    display_name = "All Sports" if sport.lower() == "all" else sport.replace("_", " ").title()
    status_msg = await interaction.followup.send(get_random_loading_message())
    
    nice_display, tips_list = await get_sports_tips(sport)
    save_tips(sport, tips_list)

    embed = discord.Embed(
        title=f"🔥 Top 4 {display_name} Hot Tips",
        description=f"📅 {datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M')} BST",
        color=0xff00ff
    )
    embed.add_field(name="Tips", value=nice_display, inline=False)
    embed.set_footer(text="V2.2 • Auto results every 30 mins • Gamble responsibly")

    await interaction.followup.send(embed=embed)
    try: await status_msg.delete()
    except: pass

@bot.event
async def on_ready():
    print(f"✅ {bot.user} V2.2 IS FIXED AND READY!")
    await bot.tree.sync()
    scheduler.start()
    scheduler.add_job(auto_check_tips, 'interval', minutes=30, next_run_time=datetime.now(pytz.timezone('Europe/London')))
    print("✅ Auto checker running every 30 mins")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
