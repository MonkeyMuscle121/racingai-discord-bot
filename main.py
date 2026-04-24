import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import logging

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

async def get_full_sports_hot_tips():
    try:
        client = AsyncClient(api_key=XAI_API_KEY, timeout=120)
        
        chat = client.chat.create(
            model="grok-4.20-reasoning",
            tools=[web_search(), x_search()],
            temperature=0.7,
            max_turns=4,
        )

        date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')
        
        prompt = f"""
Analyse within the next 48 hours: UFC, boxing, darts, horse racing, and football (soccer).
Date: {date_today}
Return exactly the top 4 hot tips in this format:

**Top 4 hot tip outcomes for the next 48 hours...**

1. **Event** – Outcome (odds if available, time in BST, why hot)
2. ...
3. ...
4. ...

For horse racing: Always include race time (e.g. 14:35 Sandown).
For football: Include league + kick-off time in BST.
Keep each tip concise.
"""

        chat.append(system("You are an expert sports betting analyst. Always use tools for real-time data. Be accurate with times in BST."))
        chat.append(user(prompt))

        response = await chat.sample()
        return response.content.strip() or "No tips generated."

    except Exception as e:
        logger.error(f"Hot tips error: {e}", exc_info=True)
        return f"❌ Error: {str(e)[:250]}"

# ====================== SLASH COMMAND ======================
@bot.tree.command(name="tips", description="Get top 4 hot sports betting tips (UFC, Boxing, Darts, Racing, Football)")
async def hot_tips(interaction: discord.Interaction):
    await interaction.response.defer()
    
    await interaction.followup.send("🔍 Pulling real-time data for UFC, Boxing, Darts, Horse Racing & Football... (30-80s)")

    analysis = await get_full_sports_hot_tips()
    
    embed = discord.Embed(
        title="🔥 Top 4 Hot Tip Outcomes",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y %H:%M')} BST\n🔥 xAI Grok Real-time",
        color=0xff00ff
    )
    
    # Safe field splitting
    if len(analysis) > 1000:
        chunks = [analysis[i:i+1000] for i in range(0, len(analysis), 1000)]
        for i, chunk in enumerate(chunks, 1):
            embed.add_field(name=f"Hot Tips (Part {i})",
