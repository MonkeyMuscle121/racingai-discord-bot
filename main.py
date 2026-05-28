import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
import json
import asyncio
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
    "🔍 Pulling **REAL** declared runners... hold tight you melt 😂",
    "🔍 Fetching live race cards...",
    "🔍 Loading accurate tips only...",
]

def get_random_loading_message():
    import random
    return random.choice(LOADING_MESSAGES)

def normalize_sport(sport: str) -> str:
    sport_lower = sport.lower().strip()
    if sport_lower in ["horse", "horses", "racing", "horse racing", "horseracing"]:
        return "horse_racing"
    return sport_lower

def clean_response(text: str) -> str:
    return '\n'.join(line.strip() for line in text.strip().split('\n'))

def format_tips_for_display(tips_list):
    if not tips_list:
        return "No upcoming events in next 48hrs."
    lines = []
    for i, tip in enumerate(tips_list, 1):
        event = tip.get("event", "Unknown Event")
        selection = tip.get("selection", "Unknown")
        time = tip.get("time", "")
        comment = tip.get("comment", "This one smells spicy 👀")
        
        time_str = f" ⏰ **{time}**" if time else ""
        lines.append(f"**{i}.** {event}{time_str}\n**Pick:** {selection}\n**Comment:** {comment}")
    return "\n\n".join(lines)

# ====================== MAX ACCURACY PROMPT ======================
async def get_sports_tips(sport: str, specific_event: str = None):
    try:
        async with asyncio.timeout(85):
            client = AsyncClient(api_key=XAI_API_KEY, timeout=80)
            chat = client.chat.create(
                model="grok-4.20-reasoning",
                tools=[web_search(), x_search()],
                temperature=0.5,
                max_turns=7,
            )
            
            now = datetime.now(pytz.timezone('Europe/London'))
            cutoff = (now + timedelta(hours=48)).strftime('%A %d %B %Y')
            
            prompt = f"""
CURRENT TIME: {now.strftime('%A %d %B %Y %H:%M BST')}
STRICT 48 HOUR RULE - ONLY include races starting from NOW until {cutoff}.

**MANDATORY:**
- Use web_search tool multiple times if needed to verify real meetings and declared runners.
- ONLY suggest horses that are actually declared to run.
- If you can't find accurate info, say so instead of guessing.

Reply with **VALID JSON ONLY**:
{{
  "tips": [
    {{"event": "Meet Name - Race Name", "selection": "Real declared horse", "time": "HH:MM", "comment": "Savage funny comment"}}
  ]
}}
Exactly 4 tips.
"""

            chat.append(system("You are a savage Racing AI bot. Be extremely accurate. Never hallucinate races or horses. Always verify with tools first. Be brutally funny."))
            chat.append(user(prompt))
            response = await chat.sample()
            
            text = clean_response(response.content)
            tips_list = []
            try:
                start = text.find('{')
                end = text.rfind('}') + 1
                if start != -1:
                    data = json.loads(text[start:end])
                    tips_list = data.get("tips", [])
            except:
                logger.warning("JSON parse failed")
            
            return format_tips_for_display(tips_list), tips_list
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return "❌ Failed to fetch real tips. Try again later.", []

# Save function + Auto Checker (kept minimal)
def save_tips(sport: str, tips_list: list, specific_event=None):
    try:
        data = {}
        if TIPS_FILE.exists():
            with open(TIPS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        key = normalize_sport(sport) + (f"_{specific_event[:20]}" if specific_event else "")
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

# Commands
@bot.tree.command(name="tips", description="Get 4 general hot tips")
async def hot_tips(interaction: discord.Interaction, sport: str = "all"):
    await interaction.response.defer(thinking=True)
    status_msg = await interaction.followup.send(get_random_loading_message())
    
    try:
        nice_display, tips_list = await get_sports_tips(sport)
        save_tips(sport, tips_list)

        embed = discord.Embed(
            title=f"🔥 Top 4 {sport.replace('_', ' ').title()} Hot Tips",
            description=f"📅 {datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M')} BST",
            color=0xff00ff
        )
        embed.add_field(name="Tips", value=nice_display, inline=False)
        embed.set_footer(text="🔥 For entertainment only • Not real betting advice • Gamble responsibly • 18+")
        await interaction.followup.send(embed=embed)
    except:
        await interaction.followup.send("❌ Error. Try again.")
    finally:
        try: await status_msg.delete()
        except: pass

@bot.event
async def on_ready():
    print(f"✅ {bot.user} V4.1 — MAX ACCURACY!")
    await bot.tree.sync()
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
