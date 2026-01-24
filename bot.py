import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import os

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

GUILD_ID = 1463251661421285388
STAFF_ROLE_NAME = "Staff"
ticket_count = 0  # egyszerű számláló (restart után nullázódik)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)  # örökké élő view

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        global ticket_count
        ticket_count += 1
        guild = interaction.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"ticket-{ticket_count}"
        ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)

        # Close gomb létrehozása
        close_view = View(timeout=None)
        close_button = Button(label="Close Ticket", style=discord.ButtonStyle.red)

        async def close_callback(close_interaction):
            await ticket_channel.delete()

        close_button.callback = close_callback
        close_view.add_item(close_button)

        await ticket_channel.send("🎫 Ticket létrehozva!", view=close_view)
        await interaction.response.send_message(f"🎟️ Ticket létrehozva: {ticket_channel.mention}", ephemeral=True)

@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    print("Bot ONLINE")

@bot.tree.command(name="panel", description="Ticket nyitó panel küldése")
async def panel(interaction: discord.Interaction):
    view = TicketView()
    await interaction.response.send_message("Nyomd meg a gombot a ticket nyitásához!", view=view, ephemeral=False)

bot.run(os.getenv("TOKEN"))
