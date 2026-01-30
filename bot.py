import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import json
import os

CONFIG_FILE = "config.json"

# ================= CONFIG =================

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

config = load_config()

def get_guild_config(guild_id: int):
    gid = str(guild_id)
    if gid not in config:
        config[gid] = {
            "ticket_counter": 0,
            "ticket_types": {}
        }
        save_config(config)
    return config[gid]

# ================= BOT =================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= BUTTON COLORS =================

BUTTON_COLORS = {
    "blurple": discord.ButtonStyle.primary,
    "green": discord.ButtonStyle.success,
    "red": discord.ButtonStyle.danger,
    "grey": discord.ButtonStyle.secondary
}

# ================= MODAL =================

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
        conf = get_guild_config(guild.id)

        conf["ticket_counter"] += 1
        counter = conf["ticket_counter"]
        save_config(config)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        ping_roles = []
        ticket_data = conf["ticket_types"][self.ticket_type]

        for role_id in ticket_data["roles"]:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
                ping_roles.append(role.mention)

        channel_name = f"{self.ticket_type}-{counter}".replace(" ", "-").lower()
        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites
        )

        await channel.send(
            f"{' '.join(ping_roles)}\n"
            f"🎫 {interaction.user.mention} nyitott egy ticketet\n\n"
            f"**Leírás:**\n{self.reason.value}"
        )

        await interaction.response.send_message(
            f"✅ Ticket létrehozva: {channel.mention}",
            ephemeral=True
        )

# ================= PANEL =================

class TicketButton(Button):
    def __init__(self, ticket_type: str, style: discord.ButtonStyle):
        super().__init__(
            label=ticket_type,
            style=style,
            custom_id=f"ticket_{ticket_type}"
        )
        self.ticket_type = ticket_type

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(self.ticket_type))

class TicketPanel(View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        conf = get_guild_config(guild_id)

        for name, data in conf["ticket_types"].items():
            color_name = data.get("color", "blurple")
            style = BUTTON_COLORS.get(color_name, discord.ButtonStyle.primary)
            self.add_item(TicketButton(name, style))

# ================= COMMANDS =================

@bot.tree.command(name="ticketpanel", description="Ticket panel küldése")
async def ticketpanel(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🎟️ Válaszd ki a ticket típusát:",
        view=TicketPanel(interaction.guild.id)
    )

@bot.tree.command(name="addtickettype", description="Új ticket típus")
@app_commands.checks.has_permissions(manage_guild=True)
async def addtickettype(
    interaction: discord.Interaction,
    name: str,
    role: discord.Role
):
    conf = get_guild_config(interaction.guild.id)

    conf["ticket_types"][name] = {
        "roles": [role.id],
        "color": "blurple"
    }

    save_config(config)

    await interaction.response.send_message(
        f"✅ Ticket típus létrehozva: **{name}**\nElső role: {role.mention}"
    )

@bot.tree.command(name="addticketrole", description="Role hozzáadása ticket típushoz")
@app_commands.checks.has_permissions(manage_guild=True)
async def addticketrole(
    interaction: discord.Interaction,
    name: str,
    role: discord.Role
):
    conf = get_guild_config(interaction.guild.id)

    if name not in conf["ticket_types"]:
        await interaction.response.send_message("❌ Nincs ilyen ticket típus.", ephemeral=True)
        return

    if role.id not in conf["ticket_types"][name]["roles"]:
        conf["ticket_types"][name]["roles"].append(role.id)
        save_config(config)

    await interaction.response.send_message(
        f"➕ {role.mention} hozzáadva **{name}** típushoz"
    )

@bot.tree.command(name="setticketcolor", description="Ticket gomb színének állítása")
@app_commands.checks.has_permissions(manage_guild=True)
async def setticketcolor(
    interaction: discord.Interaction,
    name: str,
    color: str
):
    if color not in BUTTON_COLORS:
        await interaction.response.send_message(
            "❌ Színek: blurple, green, red, grey",
            ephemeral=True
        )
        return

    conf = get_guild_config(interaction.guild.id)

    if name not in conf["ticket_types"]:
        await interaction.response.send_message("❌ Nincs ilyen ticket típus.", ephemeral=True)
        return

    conf["ticket_types"][name]["color"] = color
    save_config(config)

    await interaction.response.send_message(
        f"🎨 **{name}** gomb színe beállítva: `{color}`"
    )

# ================= READY =================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot ONLINE | {len(bot.guilds)} szerveren")

# ================= RUN =================

bot.run(os.getenv("TOKEN"))            style = BUTTON_COLORS.get(data.get("color", "blurple"))
            self.add_item(TicketButton(name, style))

class TicketButton(Button):
    def __init__(self, ticket_type: str, style):
        super().__init__(
            label=ticket_type,
            style=style,
            custom_id=f"ticket_{ticket_type}"
        )
        self.ticket_type = ticket_type

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(self.ticket_type))

# ---------------- COMMANDS ----------------

@bot.tree.command(name="ticketpanel", description="Ticket panel küldése")
async def ticketpanel(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🎟️ Válaszd ki a ticket típusát:",
        view=TicketPanel(interaction.guild.id)
    )

@bot.tree.command(name="addtickettype", description="Új ticket típus")
@app_commands.checks.has_permissions(manage_guild=True)
async def addtickettype(interaction: discord.Interaction, name: str, role: discord.Role):
    conf = get_guild_config(interaction.guild.id)
    conf["ticket_types"][name] = {
        "roles": [role.id],
        "color": "blurple"
    }
    save_config(config)
    await interaction.response.send_message(f"✅ Ticket típus létrehozva: **{name}**")

@bot.tree.command(name="addticketrole", description="Role hozzáadása ticket típushoz")
@app_commands.checks.has_permissions(manage_guild=True)
async def addticketrole(interaction: discord.Interaction, name: str, role: discord.Role):
    conf = get_guild_config(interaction.guild.id)
    conf["ticket_types"][name]["roles"].append(role.id)
    save_config(config)
    await interaction.response.send_message(f"➕ {role.mention} hozzáadva **{name}** típushoz")

@bot.tree.command(name="setticketcolor", description="Ticket gomb színe")
@app_commands.checks.has_permissions(manage_guild=True)
async def setticketcolor(interaction: discord.Interaction, name: str, color: str):
    if color not in BUTTON_COLORS:
        await interaction.response.send_message(
            "❌ Színek: blurple, green, red, grey",
            ephemeral=True
        )
        return

    conf = get_guild_config(interaction.guild.id)
    conf["ticket_types"][name]["color"] = color
    save_config(config)
    await interaction.response.send_message(f"🎨 **{name}** gomb színe: `{color}`")

# ---------------- READY ----------------

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot ONLINE | {len(bot.guilds)} szerveren")

bot.run(os.getenv("TOKEN"))        for name in guild_conf["ticket_types"]:
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
