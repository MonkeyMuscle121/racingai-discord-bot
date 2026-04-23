import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from openai import OpenAI
import asyncio

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler = AsyncIOScheduler(timezone="GMT")

async def analyze_with_ai():
    try:
        client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

        date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')

        prompt = f"""You are a professional UK & Irish horse racing tipster.
Today's date is {date_today}.

Focus ONLY on races running TODAY (Thursday 23 April 2026).

Meetings today include Warwick, Perth, Beverley, Dundalk, Southwell, etc.

Give exactly:
- 4 best bets of the day (win or each-way)
- 1 strong 4-fold accumulator

Format each bet clearly: Time - Venue - Horse - Confidence - Short reason.

Be realistic and only use today's actual racing."""

        response = await asyncio.wait_for(
            asyncio.get_running_loop().run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model="grok-4.20-reasoning",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.6,
                    max_tokens=900
                )
            ),
            timeout=18.0   # Reduced timeout
        )
        return response.choices[0].message.content

    except asyncio.TimeoutError:
        return "❌ Timeout. Please try !tips again in 30 seconds."
    except Exception as e:
        return f"❌ Error: {str(e)[:150]}"

@bot.command(name="tips")
async def manual_tips(ctx):
    msg = await ctx.send("🐎 **RacingAI Tips** – Analysing today's real cards... ⏳")
    analysis = await analyze_with_ai()
    
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
