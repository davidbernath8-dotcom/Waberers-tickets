import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import os

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

GUILD_ID = 1463251661421285388
STAFF_ROLE_NAME = "Staff"
ticket_count = 0

# Pingelendő role ID-k
PING_ROLES = [
    1463254825256091761,
    1463254505700462614,
    1463252057635946578
]

# --- Ticket Modal (nyitás) ---
class TicketModal(Modal):
    def __init__(self, user: discord.Member):
        super().__init__(title="Nyiss egy ticketet")
        self.user = user
        self.reason = TextInput(label="Miért nyitsz ticketet?", style=discord.TextStyle.paragraph)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        global ticket_count
        ticket_count += 1
        guild = interaction.guild

        # Jogosultságok
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"ticket-{ticket_count}"
        ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)

        # Close gomb  zárással
        close_view = View(timeout=None)
        close_button = Button(label="Close Ticket", style=discord.ButtonStyle.red)

        async def close_callback(close_interaction):
            class CloseModal(Modal):
                def __init__(self):
                    super().__init__(title="Zárás oka")
                    self.close_reason = TextInput(label="Miért zárja a ticketet?", style=discord.TextStyle.paragraph)
                    self.add_item(self.close_reason)

                async def on_submit(self, modal_interaction: discord.Interaction):
                    await ticket_channel.send(f"🛑 Ticket zárva!\n**Ok:** {self.close_reason.value}")
                    await ticket_channel.delete()
                    await modal_interaction.response.send_message("Ticket törölve!", ephemeral=True)

            await close_interaction.response.send_modal(CloseModal())

        close_button.callback = close_callback
        close_view.add_item(close_button)

        # Ping a három rang
        ping_text = " ".join([f"<@&{r}>" for r in PING_ROLES])
        await ticket_channel.send(f"{ping_text}\n🎫 {self.user.mention} nyitott egy ticketet!\n**Ok:** {self.reason.value}", view=close_view)
        await interaction.response.send_message(f"🎟️ Ticket létrehozva: {ticket_channel.mention}", ephemeral=True)

# --- Ticket nyitó panel ---
class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Nyiss Ticketet", style=discord.ButtonStyle.green, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        modal = TicketModal(interaction.user)
        await interaction.response.send_modal(modal)

# --- Bot events ---
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    print("Bot ONLINE")

# --- Panel parancs ---
@bot.tree.command(name="panel", description="Ticket nyitó panel")
async def panel(interaction: discord.Interaction):
    view = TicketView()
    await interaction.response.send_message("Nyomd meg a gombot a ticket nyitásához!", view=view, ephemeral=False)

bot.run(os.getenv("TOKEN"))
