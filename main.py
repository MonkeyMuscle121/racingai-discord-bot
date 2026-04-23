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

print("=== BOT STARTUP DEBUG ===")
print(f"DISCORD_TOKEN loaded: {bool(DISCORD_TOKEN)}")
print(f"Token length: {len(DISCORD_TOKEN) if DISCORD_TOKEN else 0} characters")
print(f"Token starts with: {DISCORD_TOKEN[:30] if DISCORD_TOKEN else 'None'}...")
print(f"XAI_API_KEY loaded: {bool(XAI_API_KEY)}")
print(f"CHANNEL_ID: {CHANNEL_ID}")
print("=========================")

if not DISCORD_TOKEN:
    print("❌ No DISCORD_TOKEN found!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler = AsyncIOScheduler(timezone="GMT")

async def analyze_with_ai():
    client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
    prompt = f"You are a horse racing expert on {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')}. Give 4 bets and 1 4-fold acca with short reasoning."
    try:
        resp = client.chat.completions.create(model="grok-beta", messages=[{"role": "user", "content": prompt}], temperature=0.7, max_tokens=1000)
        return resp.choices[0].message.content
    except Exception as e:
        return f"AI Error: {str(e)[:200]}"

@bot.command(name="tips")
async def manual_tips(ctx):
    await ctx.send("🐎 Generating RacingAI tips... ⏳")
    analysis = await analyze_with_ai()
    embed = discord.Embed(title="🐎 RacingAI Tips", color=0x00ff88)
    embed.add_field(name="Today's Picks", value=analysis[:4000], inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ SUCCESS: {bot.user} is ONLINE and ready! Type !tips to test.")
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
    
