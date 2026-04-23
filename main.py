import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from openai import OpenAI

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler = AsyncIOScheduler(timezone="GMT")

async def analyze_with_ai():
    if not XAI_API_KEY:
        return "❌ XAI API key missing."

    client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

    date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')

    prompt = f"""You are a professional UK & Irish horse racing analyst.
Today is {date_today}.

Today's actual race meetings include: **Warwick, Perth, Beverley, Dundalk, Southwell** and others.

Analyse form, ground conditions, weather, trainer/jockey stats, etc.

Return:
- Exactly 4 strong bets (win or each-way)
- 1 solid 4-fold accumulator

For each bet include: Race time + venue, Horse name, Bet type, Confidence (1-10), short clear reasoning.

Be realistic and use emojis."""

    try:
        response = client.chat.completions.create(
            model="grok-4.20-reasoning",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.65,
            max_tokens=1100
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ AI Error: {str(e)[:200]}"

# Manual !tips
@bot.command(name="tips")
async def manual_tips(ctx):
    msg = await ctx.send("🐎 **RacingAI Tips** – Generating now... ⏳")
    analysis = await analyze_with_ai()
    
    embed = discord.Embed(
        title="🐎 RacingAI Tips",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')}\n🔥 Powered by xAI Grok",
        color=0x00ff88,
        timestamp=datetime.now(pytz.utc)
    )
    embed.add_field(name="📌 4 Best Bets + 4-Fold Acca", value=analysis[:4096], inline=False)
    embed.set_footer(text="For entertainment only • Gamble responsibly • 18+")
    await msg.edit(embed=embed)

# Daily 10AM Post
async def daily_racing_post():
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

@scheduler.scheduled_job('cron', hour=10, minute=0, timezone='GMT')
async def scheduled_job():
    await daily_racing_post()

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
