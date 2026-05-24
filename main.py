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
    "🔍 Pulling **REAL** race cards... hold tight you melt 😂",
    "🔍 Fetching live declared runners...",
    "🔍 Loading accurate tips...",
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

# ====================== DISPLAY WITH MEET ======================
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

# ====================== STRONG PROMPT ======================
async def get_sports_tips(sport: str, specific_event: str = None):
    try:
        async with asyncio.timeout(80):
            client = AsyncClient(api_key=XAI_API_KEY, timeout=75)
            chat = client.chat.create(
                model="grok-4.20-reasoning",
                tools=[web_search(), x_search()],
                temperature=0.55,
                max_turns=6,
            )
            
            now = datetime.now(pytz.timezone('Europe/London'))
            cutoff = (now + timedelta(hours=48)).strftime('%A %d %B %Y')
            
            prompt = f"""
CURRENT TIME: {now.strftime('%A %d %B %Y %H:%M BST')}
STRICT 48 HOUR RULE: ONLY events starting from NOW until {cutoff}.

YOU MUST use web_search to get REAL upcoming {sport} meetings with correct times and declared runners.

Reply with **VALID JSON ONLY**:
{{
  "tips": [
    {{"event": "Meet Name - Race Name", "selection": "Real horse", "time": "HH:MM", "comment": "Savage funny comment"}}
  ]
}}
Exactly 4 tips.
"""

            chat.append(system("You are a savage, cheeky Racing AI bot. ALWAYS search real data first. Include the racecourse/meet name clearly in the event field. Never hallucinate. Be brutally funny."))
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
            
    except asyncio.TimeoutError:
        return "❌ Timed out. Try again.", []
    except Exception as e:
        logger.error(f"Error: {e}")
        return "❌ Failed to fetch real tips.", []

# Save & Auto Checker (unchanged from last)
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

async def check_individual_results(entry):
    try:
        client = AsyncClient(api_key=XAI_API_KEY, timeout=50)
        chat = client.chat.create(model="grok-4.20-reasoning", tools=[web_search(), x_search()], temperature=0.6, max_turns=4)
        prompt = f"Current time: {datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M BST')}\n\nTips:\n{json.dumps(entry.get('tips', []), indent=2)}\n\nMark finished ones with ✅ WON or ❌ LOST. Be savage."
        chat.append(system("You are a savage Racing AI bot."))
        chat.append(user(prompt))
        response = await chat.sample()
        return clean_response(response.content)
    except:
        return None

async def auto_check_tips():
    logger.info("🔄 Auto checking tips...")
    try:
        if not TIPS_FILE.exists(): return
        with open(TIPS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        channel = bot.get_channel(CHANNEL_ID)
        if not channel: return
        for key, entry in list(data.items()):
            if not entry.get("tips"): continue
            result = await check_individual_results(entry)
            if result and any(x in result for x in ["✅", "❌"]):
                title = f"🔄 AUTO RESULTS — {entry['sport'].title()}"
                if entry.get("event"): title += f" | {entry['event']}"
                embed = discord.Embed(title=title, description=f"📅 {entry['timestamp'][:16]}", color=0x00ff88)
                embed.add_field(name="Verdict", value=result[:3900], inline=False)
                embed.set_footer(text="✅ Won • ❌ Lost • Auto every 40 mins")
                await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Auto check error: {e}")

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
    print(f"✅ {bot.user} V3.9 — MEET NAMES FIXED!")
    await bot.tree.sync()
    scheduler.start()
    scheduler.add_job(auto_check_tips, 'interval', minutes=40, next_run_time=datetime.now(pytz.timezone('Europe/London')))

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
