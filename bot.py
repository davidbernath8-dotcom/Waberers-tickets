import discord
from discord.ext import commands
from discord import app_commands
import os

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

GUILD_ID = 123456789012345678  # A SZERVER ID

@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    print("Bot elindult")

@bot.tree.command(name="ticket", description="Ticket nyitása")
async def ticket(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🎟️ Ticket parancs működik!", ephemeral=True
    )

bot.run(os.getenv("TOKEN"))
