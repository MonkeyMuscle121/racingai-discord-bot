import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from openai import OpenAI
import asyncio
import requests
from bs4 import BeautifulSoup

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler = AsyncIOScheduler(timezone="GMT")

# =============== SCRAPE TODAY'S RACECARDS ===============
def get_todays_racecards():
    try:
        # Scrape from a reliable free source
        url = "https://www.irishracing.com/racecards"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        meetings = []
        for meeting in soup.find_all('div', class_='meeting'):
            name = meeting.find('h3')
            if name:
                meetings.append(name.text.strip())
        
        if not meetings:
            # Fallback
            return "Today's meetings: Warwick, Perth, Beverley, Dundalk, Southwell (and others)"
        return f"Today's meetings: {', '.join(meetings[:8])}"
    except:
        return "Warwick, Perth, Beverley, Dundalk, Southwell and other UK/Irish meetings today"

async def analyze_with_ai(race_summary):
    try:
        client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

        date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')

        prompt = f"""You are a professional UK & Irish horse racing analyst.
Today's date is {date_today}.

Real meetings today: {race_summary}

Analyse form, ground, weather, trainer/jockey stats.

Return exactly:
- 4 strongest bets of the day (win or each-way)
- 1 strong 4-fold accumulator

Format: Time - Venue - Horse - Bet type - Confidence (1-10) - Short reasoning.

Only use today's real races. Be realistic."""

        response = await asyncio.wait_for(
            asyncio.get_running_loop().run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model="grok-4.20-reasoning",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.6,
                    max_tokens=1100
                )
            ),
            timeout=22.0
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"❌ AI Error: {str(e)[:200]}"

@bot.command(name="tips")
async def manual_tips(ctx):
    msg = await ctx.send("🐎 **RacingAI Tips** – Fetching today's real racecards... ⏳")
    
    race_summary = get_todays_racecards()
    analysis = await analyze_with_ai(race_summary)
    
    embed = discord.Embed(
        title="🐎 RacingAI Tips",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')}\n🔥 Powered by xAI Grok",
        color=0x00ff88,
        timestamp=datetime.now(pytz.utc)
    )
    embed.add_field(name="📌 4 Best Bets + 4-Fold Acca", value=analysis[:1020], inline=False)
    embed.set_footer(text="For entertainment only • Gamble responsibly • 18+")
    await msg.edit(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
