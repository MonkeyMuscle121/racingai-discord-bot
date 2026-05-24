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
    "🔍 Finding proper punts, not just favourites... hold tight you melt 😂",
    "🔍 Digging for value bets...",
    "🔍 Loading smart tips...",
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
        comment = tip.get("comment", "This one looks decent...")
        time_str = f" ⏰ **{time}**" if time else ""
        lines.append(f"**{i}.** {event}{time_str}\n**Pick:** {selection}\n**Comment:** {comment}")
    return "\n\n".join(lines)

async def get_sports_tips(sport: str):
    try:
        async with asyncio.timeout(75):
            client = AsyncClient(api_key=XAI_API_KEY, timeout=70)
            chat = client.chat.create(
                model="grok-4.20-reasoning",
                tools=[web_search(), x_search()],
                temperature=0.6,
                max_turns=5,
            )
            
            now = datetime.now(pytz.timezone('Europe/London'))
            cutoff = (now + timedelta(hours=48)).strftime('%A %d %B %Y')
            
            prompt = f"""
CURRENT TIME: {now.strftime('%A %d %B %Y %H:%M BST')}
STRICT 48 HOUR RULE - ONLY real races from NOW until {cutoff}.

Use tools to get accurate upcoming {sport} races.
Give a good mix - some strong ones, some value.

Reply with **VALID JSON ONLY**:
{{
  "tips": [
    {{"event": "Meet Name - Race Name", "selection": "Real horse", "time": "HH:MM", "comment": "Savage funny comment"}}
  ]
}}
Exactly 4 tips.
"""

            chat.append(system("You are a savage Racing AI bot. ONLY use real data. Never hallucinate races or horses. Be brutally funny."))
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
                pass
            
            return format_tips_for_display(tips_list)
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return "❌ Failed to fetch tips. Try again."

@bot.tree.command(name="tips", description="Get 4 general hot tips")
async def hot_tips(interaction: discord.Interaction, sport: str = "horse"):
    await interaction.response.defer(thinking=True)
    status_msg = await interaction.followup.send(get_random_loading_message())
    
    try:
        nice_display = await get_sports_tips(sport)

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
    print(f"✅ {bot.user} V4.6 — FIXED!")
    await bot.tree.sync()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
