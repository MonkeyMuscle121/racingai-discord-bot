import os
from datetime import datetime
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

LOADING_MESSAGES = ["🔍 Loading tips... hang on king", "🔍 Fetching data...", "🔍 One moment..."]

def get_random_loading_message():
    import random
    return random.choice(LOADING_MESSAGES)

# ====================== FAST GET TIPS ======================
async def get_sports_tips(sport: str, specific_event: str = None):
    try:
        async with asyncio.timeout(45):   # Hard 45 second cutoff
            client = AsyncClient(api_key=XAI_API_KEY, timeout=45)
            chat = client.chat.create(
                model="grok-4.20-reasoning",
                temperature=0.7,
                max_turns=2,
            )
            
            if specific_event:
                prompt = f"Give 3 quick tips for this match: {specific_event} ({sport}). Format as simple list."
            else:
                prompt = f"Give 4 quick hot tips for {sport} right now. Format as simple list."
            
            chat.append(system("You are a savage funny Racing AI bot. Be quick and cheeky."))
            chat.append(user(prompt))
            
            response = await chat.sample()
            
            return response.content[:3900], []
            
    except asyncio.TimeoutError:
        return "❌ Request timed out. Try again.", []
    except Exception as e:
        logger.error(f"Error: {e}")
        return "❌ Bot is busy. Try again in 20 seconds.", []

# ====================== COMMANDS ======================
@bot.tree.command(name="tips", description="Get 4 general hot tips")
async def hot_tips(interaction: discord.Interaction, sport: str = "all"):
    await interaction.response.defer(thinking=True)
    status_msg = await interaction.followup.send(get_random_loading_message())
    
    try:
        display, _ = await get_sports_tips(sport)
        
        embed = discord.Embed(
            title=f"🔥 Top Tips for {sport.replace('_', ' ').title()}",
            description=f"📅 {datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M')} BST",
            color=0xff00ff
        )
        embed.add_field(name="Tips", value=display or "No tips right now", inline=False)
        embed.set_footer(text="🔥 For entertainment only • Gamble responsibly • 18+")
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send("❌ Something broke. Try again.")
        logger.error(e)
    finally:
        try: await status_msg.delete()
        except: pass

@bot.tree.command(name="tipsevent", description="Get tips for specific match")
async def tips_event(interaction: discord.Interaction, sport: str, event: str):
    await interaction.response.defer(thinking=True)
    status_msg = await interaction.followup.send(get_random_loading_message())
    
    try:
        display, _ = await get_sports_tips(sport, event)
        
        embed = discord.Embed(
            title=f"🎯 Tips for: {event}",
            description=f"📅 {datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M')} BST",
            color=0xff00ff
        )
        embed.add_field(name="Tips", value=display or "No tips right now", inline=False)
        embed.set_footer(text="🔥 For entertainment only • Gamble responsibly • 18+")
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send("❌ Failed. Try again.")
        logger.error(e)
    finally:
        try: await status_msg.delete()
        except: pass

@bot.event
async def on_ready():
    print(f"✅ {bot.user} V3.1 — ULTRA LIGHT MODE ACTIVATED!")
    await bot.tree.sync()
    print("✅ Commands synced")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
