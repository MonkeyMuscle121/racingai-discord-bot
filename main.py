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

logging.basicConfig(level=logging.DEBUG)  # ← More detailed logs
logger = logging.getLogger(__name__)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler(timezone="GMT")

async def get_full_sports_hot_tips():
    try:
        logger.info("Starting Grok API call with tools...")
        client = AsyncClient(api_key=XAI_API_KEY, timeout=90)  # Shorter timeout
        
        chat = client.chat.create(
            model="grok-4.20-reasoning",
            tools=[web_search(), x_search()],
            temperature=0.7,
            max_turns=3,   # Reduce tool loops
        )

        date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')
        
        prompt = f"""
Analyse next 48 hours: UFC, boxing, darts, horse racing.
Date: {date_today}
Return ONLY the top 4 hot tips in this exact short format:

**Top 4 hot tip outcomes...**

1. **Event** – Outcome (odds, why)
2. ...
3. ...
4. ...

Keep total response under 3000 characters.
"""

        chat.append(system("Expert sports analyst. Use tools. Be concise."))
        chat.append(user(prompt))

        logger.info("Sending request to Grok...")
        response = await chat.sample()
        
        logger.info("Received response from Grok")
        return response.content.strip() or "No tips generated."

    except asyncio.TimeoutError:
        logger.error("Timeout error")
        return "⏳ Timed out fetching live sports data. Try again later."
    except Exception as e:
        logger.error(f"Full error: {e}", exc_info=True)
        return f"❌ API Error: {str(e)[:200]}"

# ====================== SLASH COMMAND ======================
@bot.tree.command(name="tips", description="Get top 4 hot sports betting tips")
async def hot_tips(interaction: discord.Interaction):
    await interaction.response.defer()
    
    await interaction.followup.send("🔍 Pulling real-time data... (30-60s)")

    analysis = await get_full_sports_hot_tips()
    
    embed = discord.Embed(
        title="🔥 Top 4 Hot Tip Outcomes",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y %H:%M')} BST",
        color=0xff00ff
    )
    
    # Safe splitting
    if len(analysis) > 1000:
        chunks = [analysis[i:i+1000] for i in range(0, len(analysis), 1000)]
        for i, chunk in enumerate(chunks, 1):
            embed.add_field(name=f"Tips Part {i}", value=chunk, inline=False)
    else:
        embed.add_field(name="Hot Tips", value=analysis or "No data returned.", inline=False)
    
    embed.set_footer(text="xAI Grok Real-time • Bet responsibly")
    
    await interaction.followup.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    try:
        await bot.tree.sync()
        print("✅ Slash commands synced")
    except Exception as e:
        print(f"Sync issue: {e}")
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
