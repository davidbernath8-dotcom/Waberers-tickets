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
ticket_count = 0
TICKET_LOG_CHANNEL_ID = None

# Ticket típusok és pingelendő rangok
TICKET_BUTTONS = {
    "panasz": [1463254825256091761, 1463254505700462614, 1463252057635946578, 1464689743731228867],
    "rang_igenylo": [1463252057635946578],
    "uzemanyag_igenylo": [1463254825256091761, 1463254505700462614, 1463252057635946578],
    "altalanos_segitseg": [1463254825256091761, 1463254505700462614, 1463252057635946578, 1464689743731228867]
}

# -------------------- Ticket Modal --------------------
class TicketModal(Modal):
    def __init__(self, user: discord.Member, button_name: str):
        super().__init__(title=f"{button_name.replace('_',' ').title()} ticket")
        self.user = user
        self.button_name = button_name
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

        role_ids = TICKET_BUTTONS[self.button_name]
        for rid in role_ids:
            role = guild.get_role(rid)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"{self.button_name}-{ticket_count}"
        ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)

        # Attribútumok a ticket csatornához
        ticket_channel.creator = self.user
        ticket_channel.ping_roles = role_ids
        ticket_channel.claimed_by = None

        # Ticket log
        log_channel = guild.get_channel(TICKET_LOG_CHANNEL_ID) if TICKET_LOG_CHANNEL_ID else None
        if log_channel:
            await log_channel.send(f"Ticket létrehozva: {ticket_channel.name}, nyitó: {self.user.mention}")

        # Close gomb
        close_view = View(timeout=None)
        close_button = Button(label="Close Ticket", style=discord.ButtonStyle.red)

        async def close_callback(close_interaction):
            if log_channel:
                await log_channel.send(f"Ticket {ticket_channel.name} zárva. Nyitó: {ticket_channel.creator.mention}, Claim: {getattr(ticket_channel,'claimed_by','nincs')}")
            await ticket_channel.delete()
            await close_interaction.response.send_message("Ticket törölve!", ephemeral=True)

        close_button.callback = close_callback
        close_view.add_item(close_button)

        ping_text = " ".join([f"<@&{r}>" for r in role_ids])
        await ticket_channel.send(f"{ping_text}\n🎫 {self.user.mention} nyitott egy ticketet!\n**Ok:** {self.reason.value}", view=close_view)
        await interaction.response.send_message(f"🎟️ Ticket létrehozva: {ticket_channel.mention}", ephemeral=True)

# -------------------- Ticket Panel --------------------
class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="Panasz más játékosra", style=discord.ButtonStyle.red, custom_id="panasz", row=0))
        self.add_item(Button(label="Rang igénylő", style=discord.ButtonStyle.blurple, custom_id="rang_igenylo", row=1))
        self.add_item(Button(label="Üzemanyag igénylő", style=discord.ButtonStyle.green, custom_id="uzemanyag_igenylo", row=2))
        self.add_item(Button(label="Általános segítség", style=discord.ButtonStyle.gray, custom_id="altalanos_segitseg", row=3))

# -------------------- Gomb callback --------------------
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return
    custom_id = interaction.data.get("custom_id")
    if custom_id in TICKET_BUTTONS:
        modal = TicketModal(interaction.user, custom_id)
        await interaction.response.send_modal(modal)

# -------------------- /panel --------------------
@bot.tree.command(name="panel", description="Ticket nyitó panel")
async def panel(interaction: discord.Interaction):
    view = TicketView()
    await interaction.response.send_message("Nyomd meg a gombot a ticket nyitásához!", view=view, ephemeral=False)

# -------------------- /claim --------------------
@bot.tree.command(name="claim", description="Claimeld a ticketet")
async def claim(interaction: discord.Interaction):
    channel = interaction.channel
    if not hasattr(channel, "creator"):
        await interaction.response.send_message("❌ Ez nem ticket csatorna!", ephemeral=True)
        return
    if channel.claimed_by:
        await interaction.response.send_message(f"⚠️ Már claimelve: {channel.claimed_by.mention}", ephemeral=True)
        return
    channel.claimed_by = interaction.user
    await interaction.response.send_message(f"✅ {interaction.user.mention} claimelte a ticketet!", ephemeral=True)

# -------------------- /close --------------------
@bot.tree.command(name="close", description="Bezárja a ticketet")
async def close(interaction: discord.Interaction):
    channel = interaction.channel
    if not hasattr(channel, "creator"):
        await interaction.response.send_message("❌ Ez nem ticket csatorna!", ephemeral=True)
        return
    if interaction.user != channel.creator and getattr(channel,"claimed_by",None) != interaction.user:
        await interaction.response.send_message("❌ Csak a nyitó vagy claimelő zárhatja!", ephemeral=True)
        return
    log_channel = interaction.guild.get_channel(TICKET_LOG_CHANNEL_ID) if TICKET_LOG_CHANNEL_ID else None
    if log_channel:
        await log_channel.send(f"Ticket {channel.name} zárva. Nyitó: {channel.creator.mention}, Claim: {getattr(channel,'claimed_by','nincs')}")
    await channel.delete()

# -------------------- /setlog --------------------
@bot.tree.command(name="setlog", description="Állítsd be a ticket log csatornát")
@app_commands.describe(channel="A csatorna, ahova a ticket log megy")
async def setlog(interaction: discord.Interaction, channel: discord.TextChannel):
    global TICKET_LOG_CHANNEL_ID
    STAFF_ROLE_IDS = [1463254825256091761,1463254505700462614,1463252057635946578,1464689743731228867]
    if not any(role.id in STAFF_ROLE_IDS for role in interaction.user.roles):
        await interaction.response.send_message("❌ Nincs jogosultságod!", ephemeral=True)
        return
    TICKET_LOG_CHANNEL_ID = channel.id
    await interaction.response.send_message(f"✅ Ticket log csatorna beállítva: {channel.mention}", ephemeral=True)

# -------------------- Bot ready --------------------
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    print(f"Bot ONLINE: {bot.user}")

bot.run(os.getenv("TOKEN"))    if channel.claimed_by:
        await interaction.response.send_message(f"⚠️ Már claimelve: {channel.claimed_by.mention}", ephemeral=True)
        return
    channel.claimed_by = interaction.user
    await interaction.response.send_message(f"✅ {interaction.user.mention} claimelte a ticketet!", ephemeral=True)

# -------------------- /close --------------------
@bot.tree.command(name="close", description="Bezárja a ticketet")
async def close(interaction: discord.Interaction):
    channel = interaction.channel
    if not hasattr(channel, "creator"):
        await interaction.response.send_message("❌ Ez nem ticket csatorna!", ephemeral=True)
        return
    if interaction.user != channel.creator and getattr(channel,"claimed_by",None) != interaction.user:
        await interaction.response.send_message("❌ Csak a nyitó vagy claimelő zárhatja!", ephemeral=True)
        return
    log_channel = interaction.guild.get_channel(TICKET_LOG_CHANNEL_ID) if TICKET_LOG_CHANNEL_ID else None
    if log_channel:
        await log_channel.send(f"Ticket {channel.name} zárva. Nyitó: {channel.creator.mention}, Claim: {getattr(channel,'claimed_by','nincs')}")
    await channel.delete()

# -------------------- /setlog --------------------
@bot.tree.command(name="setlog", description="Állítsd be a ticket log csatornát")
@app_commands.describe(channel="A csatorna, ahova a ticket log megy")
async def setlog(interaction: discord.Interaction, channel: discord.TextChannel):
    global TICKET_LOG_CHANNEL_ID
    # Csak Staff ranggal lehet
    STAFF_ROLE_IDS = [1463254825256091761, 1463254505700462614, 1463252057635946578, 1464689743731228867]
    if not any(role.id in STAFF_ROLE_IDS for role in interaction.user.roles):
        await interaction.response.send_message("❌ Nincs jogosultságod!", ephemeral=True)
        return
    TICKET_LOG_CHANNEL_ID = channel.id
    await interaction.response.send_message(f"✅ Ticket log csatorna beállítva: {channel.mention}", ephemeral=True)

# -------------------- READY --------------------
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    print(f"Bot ONLINE: {bot.user}")

bot.run(os.getenv("TOKEN"))
