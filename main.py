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
        client = AsyncClient(api_key=XAI_API_KEY, timeout=180)  # Longer timeout for tools
        
        chat = client.chat.create(
            model="grok-4.20-reasoning",
            tools=[web_search(), x_search()],
            temperature=0.7,
            max_turns=4,          # Limit tool loops to prevent long hangs
        )

        date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')
        
        prompt = f"""
Analyse within the next 48 hours: UFC, boxing, darts, horse racing and major events.
Date: {date_today}
Return exactly the top 4 hot tips in this format only:

**Top 4 hot tip outcomes for the next 48 hours...**

1. **Event** – Outcome (odds, why hot)
2. ...
3. ...
4. ...

Use current data. Include times in BST where possible.
"""

        chat.append(system("Expert sports betting analyst. Use tools for real-time accuracy."))
        chat.append(user(prompt))

        # Use streaming so Discord sees progress
        full_response = ""
        async for chunk in chat.stream():
            if chunk.content:
                full_response += chunk.content
                # Optional: you could edit a message here for live updates

        return full_response or "No content received."

    except asyncio.TimeoutError:
        return "⏳ Request timed out. Try again in a moment (sports data searches can be slow)."
    except Exception as e:
        logger.error(f"Hot tips error: {e}", exc_info=True)
        return f"❌ Error: {str(e)[:300]}"

# ====================== SLASH COMMAND ======================
@bot.tree.command(name="tips", description="Get top 4 hot sports betting tips")
async def hot_tips(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    
    await interaction.followup.send("🔍 Analysing real-time sports data (UFC, boxing, darts, racing)... This can take 20-60 seconds.")
    
    analysis = await get_full_sports_hot_tips()
    
    embed = discord.Embed(
        title="🔥 Top 4 Hot Tip Outcomes",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y %H:%M')} BST",
        color=0xff00ff
    )
    embed.add_field(name="Tips", value=analysis[:3900] or "No tips generated.", inline=False)
    embed.set_footer(text="Powered by xAI Grok • Real-time search • Bet responsibly")
    
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
