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

# Fast loading messages
LOADING_MESSAGES = [
    "🔍 Loading tips... hold tight 😂",
    "🔍 Fetching data... 25-45s",
    "🔍 One sec king...",
]

def get_random_loading_message():
    return random.choice(LOADING_MESSAGES)

def normalize_sport(sport: str) -> str:
    sport_lower = sport.lower().strip()
    if sport_lower in ["horse", "horses", "racing", "horse racing", "horseracing"]:
        return "horse_racing"
    return sport_lower

# ====================== FAST TIP FETCH ======================
async def get_sports_tips(sport: str, specific_event: str = None):
    try:
        async with asyncio.timeout(55):  # Hard timeout
            client = AsyncClient(api_key=XAI_API_KEY, timeout=55)
            chat = client.chat.create(
                model="grok-4.20-reasoning",
                tools=[web_search(), x_search()],
                temperature=0.7,
                max_turns=2,          # Very low for speed
            )
            
            if specific_event:
                prompt = f"Give 3 quick tips for {specific_event} in {sport}. Return only JSON."
            else:
                prompt = f"Give 4 quick hot tips for {sport}. Return only JSON."
            
            chat.append(system("You are a savage Racing AI bot. Reply with short valid JSON only."))
            chat.append(user(prompt))
            
            response = await chat.sample()
            
            # Simple extraction
            text = response.content
            tips = []
            try:
                start = text.find('{')
                end = text.rfind('}') + 1
                if start != -1:
                    data = json.loads(text[start:end])
                    tips = data.get("tips", [])
            except:
                pass
                
            # Format display
            lines = []
            for i, t in enumerate(tips[:4], 1):
                event = t.get("event", specific_event or "Match")
                pick = t.get("selection", t.get("pick", "Unknown"))
                comment = t.get("comment", "Looks good...")
                lines.append(f"**{i}.** {event}\n**Pick:** {pick}\n**Comment:** {comment}")
            
            display = "\n\n".join(lines) or "No tips available right now."
            return display, tips
            
    except asyncio.TimeoutError:
        return "❌ Took too long. Try again.", []
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "❌ Bot is overloaded. Try again in 30 seconds.", []

# ====================== SAVE ======================
def save_tips(sport: str, tips_list: list, specific_event=None):
    try:
        data = {}
        if TIPS_FILE.exists():
            with open(TIPS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        key = normalize_sport(sport) + (f"_{specific_event[:15]}" if specific_event else "")
        data[key] = {
            "timestamp": datetime.now(pytz.timezone('Europe/London')).isoformat(),
            "sport": sport,
            "event": specific_event,
            "tips": tips_list
        }
        
        with open(TIPS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except:
        pass

# ====================== COMMANDS ======================
@bot.tree.command(name="tips", description="Get 4 general hot tips")
async def hot_tips(interaction: discord.Interaction, sport: str = "all"):
    await interaction.response.defer(thinking=True)
    status_msg = await interaction.followup.send(get_random_loading_message())
    
    try:
        nice_display, tips_list = await get_sports_tips(sport)
        save_tips(sport, tips_list)

        embed = discord.Embed(
            title=f"🔥 Top 4 {sport.replace('_', ' ').title()} Tips",
            description=f"📅 {datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M')} BST",
            color=0xff00ff
        )
        embed.add_field(name="Tips", value=nice_display[:3900], inline=False)
        embed.set_footer(text="🔥 For entertainment only • Gamble responsibly • 18+")
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send("❌ Something went wrong. Try again.")
        logger.error(f"Error: {e}")
    finally:
        try: await status_msg.delete()
        except: pass

@bot.tree.command(name="tipsevent", description="Get 3 tips for specific match")
async def tips_event(interaction: discord.Interaction, sport: str, event: str):
    await interaction.response.defer(thinking=True)
    status_msg = await interaction.followup.send(get_random_loading_message())
    
    try:
        nice_display, tips_list = await get_sports_tips(sport, event)
        save_tips(sport, tips_list, event)

        embed = discord.Embed(
            title=f"🎯 3 Tips for: {event}",
            description=f"📅 {datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M')} BST",
            color=0xff00ff
        )
        embed.add_field(name="Tips", value=nice_display[:3900], inline=False)
        embed.set_footer(text="🔥 For entertainment only • Gamble responsibly • 18+")
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send("❌ Failed. Try again.")
        logger.error(f"Error: {e}")
    finally:
        try: await status_msg.delete()
        except: pass

@bot.event
async def on_ready():
    print(f"✅ {bot.user} V3.0 — FAST & STABLE!")
    await bot.tree.sync()
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
