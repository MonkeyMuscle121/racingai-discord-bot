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

LOADING_MESSAGES = [
    "🔍 Pulling real upcoming events... hold tight you melt 😂",
    "🔍 Fetching fresh tips...",
    "🔍 Loading smart picks...",
]

def get_random_loading_message():
    import random
    return random.choice(LOADING_MESSAGES)

def clean_response(text: str) -> str:
    return '\n'.join(line.strip() for line in text.strip().split('\n'))

def format_tips_for_display(tips_list):
    if not tips_list:
        return "No upcoming events found in next 48 hours."
    lines = []
    for i, tip in enumerate(tips_list, 1):
        event = tip.get("event", "Unknown Event")
        selection = tip.get("selection", "Unknown")
        comment = tip.get("comment", "This one smells spicy 👀")
        lines.append(f"**{i}.** {event}\n**Pick:** {selection}\n**Comment:** {comment}")
    return "\n\n".join(lines)

async def get_sports_tips(sport: str = None, specific_event: str = None):
    try:
        async with asyncio.timeout(70):
            client = AsyncClient(api_key=XAI_API_KEY, timeout=65)
            chat = client.chat.create(
                model="grok-4.20-reasoning",
                tools=[web_search(), x_search()],
                temperature=0.6,
                max_turns=5,
            )
            
            now = datetime.now(pytz.timezone('Europe/London'))
            cutoff = (now + timedelta(hours=48)).strftime('%A %d %B %Y')
            
            if specific_event:
                prompt = f"""
CURRENT TIME: {now.strftime('%A %d %B %Y %H:%M BST')}
STRICT 48 HOUR RULE: ONLY future events starting from NOW until {cutoff}.

Give 3 tips for this specific event: {specific_event}.
"""
            else:
                prompt = f"""
CURRENT TIME: {now.strftime('%A %d %B %Y %H:%M BST')}
STRICT 48 HOUR RULE: ONLY future events starting from NOW until {cutoff}.

Give 4 varied hot tips from different sports.
"""

            prompt += """
Reply with **VALID JSON ONLY**:
{
  "tips": [
    {"event": "Event name", "selection": "Pick", "comment": "Savage funny comment"}
  ]
}
"""

            chat.append(system("You are a savage, cheeky AI betting bot. ONLY use real future events. Never include past or ongoing events. Be brutally funny. Reply with clean VALID JSON only."))
            chat.append(user(prompt))
            response = await chat.sample()
            
            text = clean_response(response.content)
            tips_list = []
            try:
                start = text.find('{')
                end = text.rfind('}') + 1
                if start != -1:
                    data = json.loads(text[start:end])
                    tips_list = data.get("tips", [])
            except:
                pass
            
            return format_tips_for_display(tips_list), tips_list
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return "❌ Failed to fetch tips. Try again.", []

# ====================== COMMANDS ======================
@bot.tree.command(name="tips", description="Get 4 varied hot tips")
async def hot_tips(interaction: discord.Interaction, sport: str = "all"):
    await interaction.response.defer(thinking=True)
    status_msg = await interaction.followup.send(get_random_loading_message())
    
    try:
        nice_display, tips_list = await get_sports_tips(sport)

        title = f"🔥 Top 4 {sport.replace('_', ' ').title()} Hot Tips" if sport.lower() != "all" else "🔥 Top 4 Varied Hot Tips"
        
        embed = discord.Embed(
            title=title,
            description=f"📅 {datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M')} BST",
            color=0xff00ff
        )
        embed.add_field(name="Tips", value=nice_display, inline=False)
        embed.set_footer(text="🔥 For entertainment only • Not real betting advice • Gamble responsibly • 18+")
        await interaction.followup.send(embed=embed)
    except:
        await interaction.followup.send("❌ Error. Try again.")
    finally:
        try: await status_msg.delete()
        except: pass

@bot.tree.command(name="tipssport", description="Get tips for a specific sport")
async def tipssport(interaction: discord.Interaction, sport: str):
    await interaction.response.defer(thinking=True)
    status_msg = await interaction.followup.send(get_random_loading_message())
    
    try:
        nice_display, tips_list = await get_sports_tips(sport)

        embed = discord.Embed(
            title=f"🔥 Top Tips for {sport.replace('_', ' ').title()}",
            description=f"📅 {datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M')} BST",
            color=0xff00ff
        )
        embed.add_field(name="Tips", value=nice_display, inline=False)
        embed.set_footer(text="🔥 For entertainment only • Not real betting advice • Gamble responsibly • 18+")
        await interaction.followup.send(embed=embed)
    except:
        await interaction.followup.send("❌ Error. Try again.")
    finally:
        try: await status_msg.delete()
        except: pass

@bot.tree.command(name="tipsevent", description="Get 3 tips for a specific event")
async def tips_event(interaction: discord.Interaction, sport: str, event: str):
    await interaction.response.defer(thinking=True)
    status_msg = await interaction.followup.send(get_random_loading_message())
    
    try:
        nice_display, tips_list = await get_sports_tips(sport, event)

        embed = discord.Embed(
            title=f"🎯 3 Tips for: {event}",
            description=f"📅 {datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M')} BST",
            color=0xff00ff
        )
        embed.add_field(name="Tips", value=nice_display, inline=False)
        embed.set_footer(text="🔥 For entertainment only • Not real betting advice • Gamble responsibly • 18+")
        await interaction.followup.send(embed=embed)
    except:
        await interaction.followup.send("❌ Error. Try again.")
    finally:
        try: await status_msg.delete()
        except: pass

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Global slash commands synced! ({len(synced)} commands)")
    except Exception as e:
        print(f"Sync error: {e}")
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
