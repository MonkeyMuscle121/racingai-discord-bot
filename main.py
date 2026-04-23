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

if not DISCORD_TOKEN:
    print("❌ ERROR: DISCORD_TOKEN is missing or empty in environment variables!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler = AsyncIOScheduler(timezone="GMT")

async def analyze_with_ai():
    client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
    date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')
    
    prompt = f"""You are an expert UK & Irish horse racing tipster for {date_today}.
Give 4 strong bets and 1 four-fold accumulator. Use emojis and be realistic."""

    try:
        resp = client.chat.completions.create(
            model="grok-beta",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1200
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"AI error: {str(e)[:200]}"

@bot.command(name="tips")
async def manual_tips(ctx):
    await ctx.send("🐎 Generating tips... ⏳")
    analysis = await analyze_with_ai()
    embed = discord.Embed(title="🐎 RacingAI Tips", description=f"📅 {date_today}", color=0x00ff88)
    embed.add_field(name="Tips", value=analysis[:4000], inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE! Type !tips to test.")
    scheduler.start()

# Daily post at 10 AM GMT
@scheduler.scheduled_job('cron', hour=10, minute=0, timezone='GMT')
async def daily_post():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send("🐎 Daily RacingAI Tips at 10:00 GMT")
        analysis = await analyze_with_ai()
        embed = discord.Embed(title="🐎 Daily Tips", color=0x00ff88)
        embed.add_field(name="Analysis", value=analysis[:4000], inline=False)
        await channel.send(embed=embed)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
