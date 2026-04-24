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
        client = AsyncClient(api_key=XAI_API_KEY, timeout=180)
        
        chat = client.chat.create(
            model="grok-4.20-reasoning",
            tools=[web_search(), x_search()],
            temperature=0.7,
            max_turns=5,
        )

        date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')
        
        prompt = f"""
Analyse within the next 48 hours: UFC, boxing, darts, horse racing and major events.
Date: {date_today}
Return exactly the top 4 hot tips in this format:

**Top 4 hot tip outcomes for the next 48 hours...**

1. **Event** – Outcome (odds if available, why hot)
2. ...
3. ...
4. ...

Keep each tip short and concise. Include participants and BST times where possible.
"""

        chat.append(system("You are an expert sports betting analyst. Always use tools for the latest accurate data. Keep responses concise."))
        chat.append(user(prompt))

        response = await chat.sample()
        return response.content.strip() or "No content received."

    except Exception as e:
        logger.error(f"Hot tips error: {e}", exc_info=True)
        return f"❌ Error: {str(e)[:300]}"

# ====================== SLASH COMMAND ======================
@bot.tree.command(name="tips", description="Get top 4 hot sports betting tips for next 48h")
async def hot_tips(interaction: discord.Interaction):
    await interaction.response.defer()
    
    await interaction.followup.send("🔍 Pulling real-time data for UFC, boxing, darts & horse racing... (30-90 seconds)")

    analysis = await get_full_sports_hot_tips()
    
    embed = discord.Embed(
        title="🔥 Top 4 Hot Tip Outcomes",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y %H:%M')} BST\n🔥 xAI Grok Real-time",
        color=0xff00ff
    )
    
    # Split long text into multiple fields (Discord max 1024 chars per field)
    if len(analysis) > 1024:
        chunks = [analysis[i:i+1000] for i in range(0, len(analysis), 1000)]
        for i, chunk in enumerate(chunks, 1):
            embed.add_field(
                name=f"Hot Tips (Part {i})", 
                value=chunk, 
                inline=False
            )
    else:
        embed.add_field(name="Hot Tips", value=analysis, inline=False)
    
    embed.set_footer(text="For entertainment only • Bet responsibly • 18+")
    
    await interaction.followup.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    try:
        await bot.tree.sync()
        print("✅ Slash commands synced")
    except Exception as e:
        print(f"Sync warning: {e}")
    
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
