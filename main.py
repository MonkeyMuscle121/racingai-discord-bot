import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from openai import OpenAI

load_dotenv()

# ===================== CONFIG =====================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler = AsyncIOScheduler(timezone="GMT")

# =============== AI ANALYSIS with xAI Grok ===============
async def analyze_with_ai():
    client = OpenAI(
        api_key=XAI_API_KEY,
        base_url="https://api.x.ai/v1"
    )
    
    date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')
    
    prompt = f"""You are an expert UK & Irish horse racing tipster.
Today is {date_today}. There are meetings at Beverley, Perth, Warwick, Southwell, Dundalk and others.

Even without full racecard data, give your best daily analysis.
Provide:
- Exactly 4 strong bets (win or each-way)
- 1 solid 4-fold accumulator

For each bet include: Race time + venue, Horse name (or strong contender), Bet type, Confidence (1-10), short reasoning, estimated odds.

Be realistic and honest. Use emojis. Format nicely."""

    try:
        response = client.chat.completions.create(
            model="grok-beta",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1400
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ xAI API error: {str(e)[:300]}"

# =============== DAILY POST AT 10AM GMT ===============
async def daily_racing_post():
    if CHANNEL_ID == 0:
        return
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return
    await channel.send("🐎 **RacingAI Daily Tips** – 10:00 GMT\nGenerating analysis... ⏳")
    analysis = await analyze_with_ai()
    embed = discord.Embed(
        title="🐎 RacingAI Daily Tips",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')}\n🔥 Powered by xAI Grok",
        color=0x00ff88,
        timestamp=datetime.now(pytz.utc)
    )
    embed.add_field(name="📌 4 Best Bets + 4-Fold Acca", value=analysis[:4096], inline=False)
    embed.set_footer(text="For entertainment only • Gamble responsibly • 18+")
    await channel.send(embed=embed)

# =============== MANUAL !tips COMMAND ===============
@bot.command(name="tips")
async def manual_tips(ctx):
    await ctx.send("🐎 **RacingAI On-Demand Tips** – Generating now... ⏳")
    analysis = await analyze_with_ai()
    embed = discord.Embed(
        title="🐎 RacingAI Tips (Manual)",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')}\n🔥 Powered by xAI Grok",
        color=0x00ff88,
        timestamp=datetime.now(pytz.utc)
    )
    embed.add_field(name="📌 4 Best Bets + 4-Fold Acca", value=analysis[:4096], inline=False)
    embed.set_footer(text="For entertainment only • Gamble responsibly • 18+")
    await ctx.send(embed=embed)

# =============== SCHEDULER & STARTUP ===============
@scheduler.scheduled_job('cron', hour=10, minute=0, timezone='GMT')
async def scheduled_job():
    await daily_racing_post()

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online and ready! Type !tips to test.")
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
