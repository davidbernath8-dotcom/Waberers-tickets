import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import os

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

GUILD_ID = 1463251661421285388  # szerver ID
TICKET_LOG_CHANNEL = 1464729469360279563  # ide logoljuk a ticketeket
ticket_count = 0

# -------------------- Ticket Gombok és rangok --------------------
TICKET_BUTTONS = {
    "panasz": [1463254825256091761, 1463254505700462614, 1463252057635946578, 1464689743731228867],
    "rang_igenylo": [1463252057635946578],
    "uzemanyag_igenylo": [1463254825256091761, 1463254505700462614, 1463252057635946578],
    "altalanos_segitseg": [1463254825256091761, 1463254505700462614, 1463252057635946578, 1464689743731228867]
}

# -------------------- Ticket Modal --------------------
class TicketModal(Modal):
    def __init__(self, user: discord.Member, button_name: str):
        super().__init__(title=f"{button_name} ticket")
        self.user = user
        self.button_name = button_name
        self.reason = TextInput(label="Miért nyitsz ticketet?", style=discord.TextStyle.paragraph)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        global ticket_count
        ticket_count += 1
        guild = interaction.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Pingelt rangok
        role_ids = TICKET_BUTTONS[self.button_name]
        for rid in role_ids:
            role = guild.get_role(rid)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"{self.button_name}-{ticket_count}"
        ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)

        # Claim tracking
        ticket_channel.claimed_by = None
        ticket_channel.creator = self.user

        # Close gomb
        close_view = View(timeout=None)
        close_button = Button(label="Close Ticket", style=discord.ButtonStyle.red)

        async def close_callback(close_interaction):
            await ticket_channel.send(f"🛑 Ticket zárva!")
            log_channel = guild.get_channel(TICKET_LOG_CHANNEL)
            if log_channel:
                await log_channel.send(f"Ticket {ticket_channel.name} zárva. Nyitó: {ticket_channel.creator.mention}, Claim: {getattr(ticket_channel, 'claimed_by', 'nincs')}")
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
        for name in TICKET_BUTTONS.keys():
            self.add_item(Button(label=name.replace("_", " ").title(), style=discord.ButtonStyle.green, custom_id=name))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True  # mindenki nyithat

    async def on_timeout(self):
        pass

    async def on_error(self, error, item, interaction):
        print("Ticket Panel Error:", error)

    @discord.ui.button(label="dummy", style=discord.ButtonStyle.gray, custom_id="dummy", row=0)
    async def dummy_button(self, interaction: discord.Interaction, button: Button):
        pass  # semmi

    async def on_button_click(self, interaction: discord.Interaction):
        button_id = interaction.data["custom_id"]
        if button_id in TICKET_BUTTONS:
            modal = TicketModal(interaction.user, button_id)
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
    if interaction.user != channel.creator and getattr(channel, "claimed_by", None) != interaction.user:
        await interaction.response.send_message("❌ Csak a nyitó vagy claimelő zárhatja!", ephemeral=True)
        return
    guild = interaction.guild
    log_channel = guild.get_channel(TICKET_LOG_CHANNEL)
    if log_channel:
        await log_channel.send(f"Ticket {channel.name} zárva. Nyitó: {channel.creator.mention}, Claim: {getattr(channel, 'claimed_by', 'nincs')}")
    await channel.delete()

# -------------------- READY --------------------
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    print(f"Bot ONLINE: {bot.user}")

bot.run(os.getenv("TOKEN"))    async def on_submit(self, interaction: discord.Interaction):
        global ticket_count
        ticket_count += 1
        guild = interaction.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"ticket-{ticket_count}"
        ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)

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

        ping_text = " ".join([f"<@&{r}>" for r in PING_ROLES])
        await ticket_channel.send(f"{ping_text}\n🎫 {self.user.mention} nyitott egy ticketet!\n**Ok:** {self.reason.value}", view=close_view)
        await interaction.response.send_message(f"🎟️ Ticket létrehozva: {ticket_channel.mention}", ephemeral=True)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Nyiss Ticketet", style=discord.ButtonStyle.green, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        modal = TicketModal(interaction.user)
        await interaction.response.send_modal(modal)

@bot.tree.command(name="panel", description="Ticket nyitó panel")
async def panel(interaction: discord.Interaction):
    view = TicketView()
    await interaction.response.send_message("Nyomd meg a gombot a ticket nyitásához!", view=view, ephemeral=False)

# -------------------- BOT READY --------------------
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    print(f"Bot ONLINE: {bot.user}")

# -------------------- RUN --------------------
bot.run(os.getenv("TOKEN"))
