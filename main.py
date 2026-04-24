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

SPORT_CONFIG = {
    "all": {"emoji": "🔥", "color": 0xff00ff, "name": "All Sports"},
    "football": {"emoji": "⚽", "color": 0x00ff88, "name": "Football"},
    "horse_racing": {"emoji": "🐎", "color": 0xffaa00, "name": "Horse Racing"},
    "ufc": {"emoji": "🥊", "color": 0xff0000, "name": "UFC"},
    "boxing": {"emoji": "🥊", "color": 0xff0000, "name": "Boxing"},
    "darts": {"emoji": "🎯", "color": 0x00aaff, "name": "Darts"},
    "bangers": {"emoji": "💣", "color": 0xffff00, "name": "Bangers"},
}

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
            temperature=0.85,
            max_turns=6,
        )

        date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')

        if sport == "bangers":
            sport_display = "Bangers"
            extra = "Only high confidence bangers (80%+)."
        else:
            sport_display = "All Sports" if sport == "all" else ("Horse Racing" if sport == "horse_racing" else sport.replace("_", " ").title())
            extra = ""

        prompt = f"""
Current date: {date_today} BST. STRICT: Only next 48 hours.

Return exactly 4 tips in this format:

**1. Event** – Bet (odds) | **Date + Time BST** | **Confidence: XX%** [COLOURED BAR]  
→ Savage funny bantery line.

Make the confidence bar visual and coloured:
- 90%+ = 🔥🔥🔥🔥🔥 RED HOT
- 75-89% = 🟠🟠🟠🟠🟠 STRONG
- 60-74% = 🟡🟡🟡🟡🟡 SOLID
- Below 60% = ⚪⚪⚪⚪⚪

Use mum/dad/nan/grandad/sister/brother jokes. Swearing fine.
"""

        chat.append(system("""You are a savage, cheeky Racing AI bot. Always show a coloured confidence bar using the exact emoji system above. Make tips funny and entertaining."""))
        
        chat.append(user(prompt))

        response = await chat.sample()
        cleaned = clean_response(response.content)
        return cleaned or "No upcoming events in next 48 hours."

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return f"❌ Error fetching tips: {str(e)[:200]}"

# ====================== SLASH COMMAND ======================
@bot.tree.command(name="tips", description="Get hot tips - e.g. /tips football, /tips horse, /tips bangers")
async def hot_tips(interaction: discord.Interaction, sport
