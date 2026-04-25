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

# ====================== CHEEKY BANTER TIPS FUNCTION ======================
async def get_sports_tips(sport: str):
    try:
        normalized = normalize_sport(sport)
       
        client = AsyncClient(api_key=XAI_API_KEY, timeout=120)
       
        chat = client.chat.create(
            model="grok-4",
            tools=[web_search(), x_search()],
            temperature=0.85,
            max_turns=5,
        )
        
        date_today = datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y')
       
        sport_display = "Horse Racing" if normalized == "horse_racing" else sport.replace("_", " ").title()
       
        prompt = f"""
Current date: {date_today}. Use BST times.

Return **exactly** the top 4 hot tips in this format:

**Top 4 {sport_display} Hot Tips...**

1. **Event** – Specific bet (exact horses/teams/fighters, odds if available, **precise BST time**)
   → Then one savage, cheeky, funny one-liner
