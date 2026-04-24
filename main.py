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
        client = AsyncClient(api_key=XAI_API_KEY, timeout=90)
        
        chat = client.chat.create(
            model="grok-4.20-reasoning",
            tools=[web_search(), x_search()],
            temperature=0.7,
            max_turns=3,
        )

        date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')
        
        prompt = f"""
Quick analysis for next 48 hours: UFC, boxing, darts, horse racing, football.
Date: {date_today}
Return ONLY top 4 hot tips. Keep total response short.

**Top 4 hot tip outcomes...**

1. **Event** – Outcome (odds, time BST, why)
2. ...
3. ...
4. ...

Horse racing: include race time. Football: include kick-off time.
"""

        chat.append(system("Expert sports betting analyst. Use tools quickly. Stay concise."))
        chat.append(user(prompt))

        response = await chat.sample()
        return response.content.strip() or "No tips available."

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return f"❌ Error fetching tips: {str(e)[:150]}"

# ====================== SLASH COMMAND ======================
@bot.tree.command(name="tips", description="Get top 4 hot sports betting tips")
async def hot_tips(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    
    status_msg = await interaction.followup.send("🔍 Analysing real-time data for UFC, Boxing, Darts, Racing & Football...")

    analysis = await get_full_sports_hot_tips()
    
    embed = discord.Embed(
        title="🔥 Top 4 Hot Tip Outcomes",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y %H:%M')} BST",
        color=0xff00ff
    )
    
    # Safe splitting for long responses
    if len(analysis) > 1000:
        chunks = [analysis[i:i+1000] for i in range(0, len(analysis), 1000)]
        for i, chunk in enumerate(chunks, 1):
            embed.add_field(name=f"Hot Tips (Part {i})", value=chunk, inline=False)
    else:
        embed.add_field(name="Hot Tips", value=analysis or "No data at the moment.", inline=False)
    
    embed.set_footer(text="xAI Grok • Bet responsibly • 18+")
    
    await interaction.followup.send(embed=embed)
    
    # Clean up status message
    try:
        await status_msg.delete()
    except:
        pass

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
