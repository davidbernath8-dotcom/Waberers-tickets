import discord
from discord.ext import commands
from discord import app_commands
import os

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

GUILD_ID = 123456789012345678  # szerver ID-d
STAFF_ROLE_NAME = "Staff"      # staff role neve

ticket_count = 0  # egyszerű számláló (újraindításkor nullázódik)

@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    print("Bot ONLINE")

@bot.tree.command(name="ticket", description="Nyiss egy ticketet")
async def ticket(interaction: discord.Interaction):
    global ticket_count
    ticket_count += 1
    guild = interaction.guild

    # Jogosultságok
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }

    staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
    if staff_role:
        overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    # Csatorna létrehozás
    channel_name = f"ticket-{ticket_count}"
    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        overwrites=overwrites
    )

    await interaction.response.send_message(f"🎟️ Ticket létrehozva: {ticket_channel.mention}", ephemeral=True)

bot.run(os.getenv("TOKEN"))
