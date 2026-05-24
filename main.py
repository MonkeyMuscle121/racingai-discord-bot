import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
import asyncio
from pathlib import Path

# xAI SDK
from xai_sdk import AsyncClient
from xai_sdk.chat import user, system

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler(timezone="Europe/London")

LOADING_MESSAGES = [
    "🔍 Finding proper punts... hold tight you melt 😂",
    "🔍 Digging for value bets...",
    "🔍 Loading smart tips...",
]

def get_random_loading_message():
    import random
    return random.choice(LOADING_MESSAGES)

# ====================== SIMPLE & ROBUST ======================
async def get_sports_tips(sport: str):
    try:
        async with asyncio.timeout(60):
            client = AsyncClient(api_key=XAI_API_KEY, timeout=55)
            chat = client.chat.create(
                model="grok-4.20-reasoning",
                temperature=0.7,
                max_turns=3,
            )
            
            prompt = f"Give 4 good {sport} tips right now with a mix of favourites and value. Be savage and funny. Just reply normally."
            
            chat.append(system("You are a savage, cheeky Racing AI bot. Be funny and brutal."))
            chat.append(user(prompt))
            response = await chat.sample()
            
            return response.content[:3900]
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return "❌ Failed to fetch tips. Try again."

# ====================== COMMAND ======================
@bot.tree.command(name="tips", description="Get 4 general hot tips")
async def hot_tips(interaction: discord.Interaction, sport: str = "horse"):
    await interaction.response.defer(thinking=True)
    status_msg = await interaction.followup.send(get_random_loading_message())
    
    try:
        display = await get_sports_tips(sport)

        embed = discord.Embed(
            title=f"🔥 Top 4 {sport.replace('_', ' ').title()} Hot Tips",
            description=f"📅 {datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M')} BST",
            color=0xff00ff
        )
        embed.add_field(name="Tips", value=display or "No tips right now", inline=False)
        embed.set_footer(text="🔥 For entertainment only • Gamble responsibly • 18+")
        await interaction.followup.send(embed=embed)
    except:
        await interaction.followup.send("❌ Error. Try again.")
    finally:
        try: await status_msg.delete()
        except: pass

@bot.event
async def on_ready():
    print(f"✅ {bot.user} V4.5 SIMPLE MODE — BACK TO BASICS!")
    await bot.tree.sync()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
