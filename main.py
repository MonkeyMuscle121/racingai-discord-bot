import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from groq import Groq

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler = AsyncIOScheduler(timezone="GMT")

async def analyze_with_ai():
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        prompt = f"""You are a professional horse racing tipster.
Today: {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')}

Give:
- 4 strong bets (win or each-way)
- 1 4-fold accumulator

Keep responses clear and use emojis."""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error: {str(e)[:200]}"

@bot.command(name="tips")
async def manual_tips(ctx):
    await ctx.send("🐎 **RacingAI Tips** – Generating now... ⏳")
    analysis = await analyze_with_ai()
    
    embed = discord.Embed(
        title="🐎 RacingAI Tips",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')}",
        color=0x00ff88
    )
    embed.add_field(name="📌 4 Best Bets + 4-Fold", value=analysis[:4000], inline=False)
    embed.set_footer(text="For entertainment only • Gamble responsibly")
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
