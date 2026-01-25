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
# ------------------------
# ===== MOD PARANCSOK =====
from datetime import timedelta
from discord import app_commands

# Staff role ID-k (ezek maradnak)
STAFF_ROLE_IDS = [
    1463254825256091761,
    1463254505700462614,
    1463252057635946578
]

def is_staff(interaction: discord.Interaction) -> bool:
    return any(role.id in STAFF_ROLE_IDS for role in interaction.user.roles)

# -------- BAN --------
@bot.tree.command(name="ban", description="Felhasználó kitiltása")
@app_commands.describe(user="Felhasználó", reason="Indok")
async def ban(
    interaction: discord.Interaction,
    user: discord.Member,
    reason: str = "Nincs megadva"
):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Nincs jogosultságod.", ephemeral=True)
        return

    await user.ban(reason=reason)
    await interaction.response.send_message(
        f"🔨 {user.mention} bannolva.\n**Ok:** {reason}"
    )

# -------- KICK --------
@bot.tree.command(name="kick", description="Felhasználó kirúgása")
@app_commands.describe(user="Felhasználó", reason="Indok")
async def kick(
    interaction: discord.Interaction,
    user: discord.Member,
    reason: str = "Nincs megadva"
):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Nincs jogosultságod.", ephemeral=True)
        return

    await user.kick(reason=reason)
    await interaction.response.send_message(
        f"👢 {user.mention} kickelve.\n**Ok:** {reason}"
    )

# -------- TIMEOUT --------
@bot.tree.command(name="timeout", description="Timeout adása")
@app_commands.describe(
    user="Felhasználó",
    minutes="Perc",
    reason="Indok"
)
async def timeout(
    interaction: discord.Interaction,
    user: discord.Member,
    minutes: int,
    reason: str = "Nincs megadva"
):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Nincs jogosultságod.", ephemeral=True)
        return

    until = discord.utils.utcnow() + timedelta(minutes=minutes)
    await user.timeout(until, reason=reason)

    await interaction.response.send_message(
        f"⏳ {user.mention} timeoutolva **{minutes} percre**.\n**Ok:** {reason}"
    )

# -------- UNTIMEOUT --------
@bot.tree.command(name="untimeout", description="Timeout levétele")
@app_commands.describe(user="Felhasználó")
async def untimeout(interaction: discord.Interaction, user: discord.Member):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Nincs jogosultságod.", ephemeral=True)
        return

    await user.timeout(None)
    await interaction.response.send_message(
        f"✅ {user.mention} timeout feloldva."
    )

# -------- AFK --------
afk_users = {}

@bot.tree.command(name="afk", description="AFK státusz beállítása")
@app_commands.describe(reason="AFK indok")
async def afk(interaction: discord.Interaction, reason: str = "AFK"):
    afk_users[interaction.user.id] = reason
    await interaction.response.send_message(
        f"💤 AFK mód bekapcsolva: **{reason}**",
        ephemeral=True
)
    
bot.run(os.getenv("TOKEN"))
