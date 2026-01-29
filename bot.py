import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import json
import os

CONFIG_FILE = "config.json"

# ---------------- CONFIG KEZELÉS ----------------

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

config = load_config()

def get_guild_config(guild_id: int):
    if str(guild_id) not in config:
        config[str(guild_id)] = {
            "ticket_counter": 0,
            "ticket_types": {},
            "log_channel": None
        }
        save_config(config)
    return config[str(guild_id)]

# ---------------- BOT ----------------

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- UTILS ----------------

def is_staff(member: discord.Member) -> bool:
    return member.guild_permissions.manage_guild

# ---------------- TICKET MODAL ----------------

class TicketModal(Modal):
    def __init__(self, ticket_type: str):
        super().__init__(title=f"{ticket_type} ticket")
        self.ticket_type = ticket_type
        self.reason = TextInput(
            label="Írd le a problémád",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        guild_conf = get_guild_config(guild.id)

        guild_conf["ticket_counter"] += 1
        counter = guild_conf["ticket_counter"]
        save_config(config)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        role_ids = guild_conf["ticket_types"][self.ticket_type]
        ping_roles = []

        for role_id in role_ids:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
                ping_roles.append(role.mention)

        channel_name = f"{self.ticket_type}-{counter}".lower().replace(" ", "-")
        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites
        )

        ping_text = " ".join(ping_roles) if ping_roles else ""

        await channel.send(
            f"{ping_text}\n🎫 {interaction.user.mention} nyitott egy ticketet.\n\n**Leírás:**\n{self.reason.value}"
        )

        await interaction.response.send_message(
            f"✅ Ticket létrehozva: {channel.mention}",
            ephemeral=True
        )

        if guild_conf["log_channel"]:
            log_channel = guild.get_channel(guild_conf["log_channel"])
            if log_channel:
                await log_channel.send(
                    f"📑 Ticket nyitva: {channel.mention} | {interaction.user}"
                )

# ---------------- PANEL VIEW ----------------

class TicketPanel(View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        guild_conf = get_guild_config(guild_id)

        for name in guild_conf["ticket_types"]:
            self.add_item(TicketButton(name))

class TicketButton(Button):
    def __init__(self, ticket_type: str):
        super().__init__(
            label=ticket_type,
            style=discord.ButtonStyle.primary,
            custom_id=f"ticket_{ticket_type}"
        )
        self.ticket_type = ticket_type

    async def callback(self, interaction: discord.Interaction):
        modal = TicketModal(self.ticket_type)
        await interaction.response.send_modal(modal)

# ---------------- SLASH PARANCSOK ----------------

@bot.tree.command(name="ticketpanel", description="Ticket panel küldése")
async def ticketpanel(interaction: discord.Interaction):
    view = TicketPanel(interaction.guild.id)
    await interaction.response.send_message(
        "🎟️ Válaszd ki a ticket típusát:",
        view=view
    )

# -------- TICKET TÍPUS KEZELÉS --------

@bot.tree.command(name="tickettypes", description="Ticket típus kezelő")
@app_commands.checks.has_permissions(manage_guild=True)
async def tickettypes(interaction: discord.Interaction):
    guild_conf = get_guild_config(interaction.guild.id)

    if not guild_conf["ticket_types"]:
        await interaction.response.send_message(
            "❌ Nincs egy ticket típus sem beállítva.",
            ephemeral=True
        )
        return

    text = "**Ticket típusok:**\n"
    for name, roles in guild_conf["ticket_types"].items():
        text += f"- **{name}** → {len(roles)} role\n"

    await interaction.response.send_message(text, ephemeral=True)

@bot.tree.command(name="addtickettype", description="Új ticket típus hozzáadása")
@app_commands.checks.has_permissions(manage_guild=True)
async def addtickettype(
    interaction: discord.Interaction,
    name: str,
    role: discord.Role
):
    guild_conf = get_guild_config(interaction.guild.id)

    if name not in guild_conf["ticket_types"]:
        guild_conf["ticket_types"][name] = []

    if role.id not in guild_conf["ticket_types"][name]:
        guild_conf["ticket_types"][name].append(role.id)

    save_config(config)

    await interaction.response.send_message(
        f"✅ **{name}** ticket típushoz hozzáadva: {role.mention}"
    )

# -------- LOG CHANNEL --------

@bot.tree.command(name="set_ticket_log", description="Ticket log csatorna beállítása")
@app_commands.checks.has_permissions(manage_guild=True)
async def set_ticket_log(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    guild_conf = get_guild_config(interaction.guild.id)
    guild_conf["log_channel"] = channel.id
    save_config(config)

    await interaction.response.send_message(
        f"📁 Ticket log csatorna beállítva: {channel.mention}"
    )

# ---------------- READY ----------------

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot ONLINE | {len(bot.guilds)} szerveren")

# ---------------- RUN ----------------

bot.run(os.getenv("TOKEN"))
