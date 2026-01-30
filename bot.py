import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import json
import os

CONFIG_FILE = "tickets.json"

# -------------------
# CONFIG FUNKCIÓK
# -------------------

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

config = load_config()

def get_guild_conf(guild_id: int):
    gid = str(guild_id)
    if gid not in config:
        config[gid] = {
            "counter": 0,
            "types": {},
            "log_channel_id": None,
            "claims": {}
        }
        save_config(config)
    return config[gid]

# -------------------
# BOT INIT
# -------------------

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

BUTTON_COLORS = {
    "blue": discord.ButtonStyle.primary,
    "green": discord.ButtonStyle.success,
    "red": discord.ButtonStyle.danger,
    "grey": discord.ButtonStyle.secondary
}

# -------------------
# TICKET MODAL
# -------------------

class TicketModal(Modal):
    def __init__(self, ticket_type: str):
        super().__init__(title=f"{ticket_type} ticket")
        self.ticket_type = ticket_type
        self.reason = TextInput(label="Írd le a problémát", style=discord.TextStyle.paragraph)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        conf = get_guild_conf(guild.id)
        conf["counter"] += 1
        counter = conf["counter"]
        save_config(config)

        data = conf["types"][self.ticket_type]
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        mentions = []
        for role_id in data["roles"]:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
                mentions.append(role.mention)

        channel_name = f"{self.ticket_type}-{counter}".replace(" ", "-").lower()
        channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)

        await channel.send(
            f"{' '.join(mentions)}\n🎫 {interaction.user.mention} nyitott egy ticketet\n**Leírás:** {self.reason.value}"
        )

        # Log
        log_id = conf.get("log_channel_id")
        if log_id:
            log_ch = guild.get_channel(log_id)
            if log_ch:
                await log_ch.send(f"🎫 Ticket nyitva: {channel.mention} | {interaction.user.mention} | típus: {self.ticket_type}")

        await interaction.response.send_message(f"✅ Ticket létrehozva: {channel.mention}", ephemeral=True)

# -------------------
# TICKET PANEL
# -------------------

class TicketButton(Button):
    def __init__(self, name: str, style: discord.ButtonStyle):
        super().__init__(label=name, style=style)
        self.ticket_type = name

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(self.ticket_type))

class TicketPanel(View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        conf = get_guild_conf(guild_id)
        for name, data in conf["types"].items():
            color = data.get("color", "blue")
            style = BUTTON_COLORS.get(color, discord.ButtonStyle.primary)
            self.add_item(TicketButton(name, style))

# -------------------
# COMMANDS
# -------------------

@bot.tree.command(name="ticketpanel", description="Ticket panel küldése")
async def ticketpanel(interaction: discord.Interaction):
    await interaction.response.send_message("🎟 Válaszd ki a ticket típusát:", view=TicketPanel(interaction.guild.id))

@bot.tree.command(name="addtickettype", description="Új ticket típus")
@app_commands.checks.has_permissions(manage_guild=True)
async def addtickettype(interaction: discord.Interaction, name: str, role: discord.Role):
    conf = get_guild_conf(interaction.guild.id)
    conf["types"][name] = {"roles": [role.id], "color": "blue"}
    save_config(config)
    await interaction.response.send_message(f"✅ Ticket típus létrehozva: **{name}** | Role: {role.mention}")

@bot.tree.command(name="addticketrole", description="Role hozzáadása tickethez")
@app_commands.checks.has_permissions(manage_guild=True)
async def addticketrole(interaction: discord.Interaction, name: str, role: discord.Role):
    conf = get_guild_conf(interaction.guild.id)
    if name not in conf["types"]:
        await interaction.response.send_message("❌ Nincs ilyen ticket típus.", ephemeral=True)
        return
    if role.id not in conf["types"][name]["roles"]:
        conf["types"][name]["roles"].append(role.id)
        save_config(config)
    await interaction.response.send_message(f"➕ {role.mention} hozzáadva **{name}** tickethez")

@bot.tree.command(name="setticketcolor", description="Ticket gomb színe")
@app_commands.checks.has_permissions(manage_guild=True)
async def setticketcolor(interaction: discord.Interaction, name: str, color: str):
    if color not in BUTTON_COLORS:
        await interaction.response.send_message("❌ Színek: blue, green, red, grey", ephemeral=True)
        return
    conf = get_guild_conf(interaction.guild.id)
    if name not in conf["types"]:
        await interaction.response.send_message("❌ Nincs ilyen ticket típus.", ephemeral=True)
        return
    conf["types"][name]["color"] = color
    save_config(config)
    await interaction.response.send_message(f"🎨 **{name}** színe beállítva: `{color}`")

@bot.tree.command(name="setlogchannel", description="Ticket log csatorna beállítása")
@app_commands.checks.has_permissions(manage_guild=True)
async def setlogchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    conf = get_guild_conf(interaction.guild.id)
    conf["log_channel_id"] = channel.id
    save_config(config)
    await interaction.response.send_message(f"✅ Log csatorna beállítva: {channel.mention}")

# -------------------
# CLAIM / CLOSE
# -------------------

@bot.tree.command(name="claim", description="Claimeld a ticketet")
async def claim(interaction: discord.Interaction):
    channel = interaction.channel
    conf = get_guild_conf(interaction.guild.id)
    if not channel.name.startswith(tuple(conf["types"].keys())):
        await interaction.response.send_message("❌ Ez nem ticket csatorna.", ephemeral=True)
        return
    conf["claims"][channel.id] = interaction.user.id
    save_config(config)
    await interaction.response.send_message(f"✅ {interaction.user.mention} claimelte ezt a ticketet.")

@bot.tree.command(name="close", description="Bezárja a ticketet")
async def close(interaction: discord.Interaction):
    channel = interaction.channel
    conf = get_guild_conf(interaction.guild.id)
    if not channel.name.startswith(tuple(conf["types"].keys())):
        await interaction.response.send_message("❌ Ez nem ticket csatorna.", ephemeral=True)
        return
    # Log
    log_id = conf.get("log_channel_id")
    if log_id:
        log_ch = interaction.guild.get_channel(log_id)
        if log_ch:
            await log_ch.send(f"✅ Ticket lezárva: {channel.mention} | Claimed: {conf['claims'].get(channel.id, 'N/A')}")
    await channel.delete()
    conf["claims"].pop(channel.id, None)
    save_config(config)

# -------------------
# READY
# -------------------

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot ONLINE | {len(bot.guilds)} szerveren")

# -------------------
# RUN
# -------------------

if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"))
