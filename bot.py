import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import json
import os

# ================== ALAP ==================

TOKEN = os.getenv("TOKEN")
CONFIG_FILE = "ticket_config.json"

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================== CONFIG ==================

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

config = load_config()

def get_guild_conf(guild_id: int):
    gid = str(guild_id)
    if gid not in config:
        config[gid] = {
            "ticket_types": {},
            "open_tickets": {},
            "log_channel": None
        }
        save_config(config)
    return config[gid]

# ================== SZÍNEK ==================

BUTTON_COLORS = {
    "kek": discord.ButtonStyle.primary,
    "zold": discord.ButtonStyle.success,
    "piros": discord.ButtonStyle.danger,
    "szurke": discord.ButtonStyle.secondary,
    "narancs": discord.ButtonStyle.secondary
}

# ================== PANEL ==================

class TicketPanel(View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.build()

    def build(self):
        self.clear_items()
        conf = get_guild_conf(self.guild_id)

        for name, data in conf["ticket_types"].items():
            style = BUTTON_COLORS.get(data["color"], discord.ButtonStyle.primary)
            button = Button(label=name, style=style)

            async def callback(interaction: discord.Interaction, ticket_name=name):
                await create_ticket(interaction, ticket_name)

            button.callback = callback
            self.add_item(button)

# ================== TICKET CREATE ==================

async def create_ticket(interaction: discord.Interaction, ticket_type: str):
    conf = get_guild_conf(interaction.guild.id)

    if ticket_type not in conf["ticket_types"]:
        await interaction.response.send_message(
            "❌ Ez a ticket típus már nem létezik.",
            ephemeral=True
        )
        return

    ticket_number = len(conf["open_tickets"]) + 1
    channel_name = f"{ticket_type}-{ticket_number}".lower().replace(" ", "-")

    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }

    for role_id in conf["ticket_types"][ticket_type]["roles"]:
        role = interaction.guild.get_role(role_id)
        if role:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    channel = await interaction.guild.create_text_channel(
        channel_name,
        overwrites=overwrites
    )

    conf["open_tickets"][str(channel.id)] = {
        "type": ticket_type,
        "owner": interaction.user.id,
        "claimed_by": None
    }
    save_config(config)

    pings = " ".join(f"<@&{r}>" for r in conf["ticket_types"][ticket_type]["roles"])
    await channel.send(
        f"{pings}\n🎫 Ticket nyitva: {interaction.user.mention}"
    )

    await interaction.response.send_message(
        f"✅ Ticket létrehozva: {channel.mention}",
        ephemeral=True
    )

# ================== SLASH PARANCSOK ==================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot online | {bot.user}")

# -------- PANEL --------
@bot.tree.command(name="panel", description="Ticket panel küldése")
async def panel(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🎟 Válaszd ki a ticket típusát:",
        view=TicketPanel(interaction.guild.id)
    )

# -------- TICKET TYPE ADD --------
@bot.tree.command(name="ticket_type", description="Ticket típus létrehozása")
@app_commands.checks.has_permissions(manage_guild=True)
async def ticket_type(
    interaction: discord.Interaction,
    name: str,
    roles: str,
    color: str = "kek"
):
    try:
        role_ids = [int(r.strip()) for r in roles.split(",")]
    except ValueError:
        await interaction.response.send_message(
            "❌ Hibás role ID formátum.",
            ephemeral=True
        )
        return

    if color not in BUTTON_COLORS:
        await interaction.response.send_message(
            "❌ Színek: kek, zold, piros, szurke, narancs",
            ephemeral=True
        )
        return

    conf = get_guild_conf(interaction.guild.id)
    conf["ticket_types"][name] = {
        "roles": role_ids,
        "color": color
    }
    save_config(config)

    await interaction.response.send_message(
        f"✅ Ticket típus létrehozva: **{name}**",
        ephemeral=True
    )

# -------- TICKET TYPE DELETE --------
@bot.tree.command(name="ticket_type_delete", description="Ticket típus törlése")
@app_commands.checks.has_permissions(manage_guild=True)
async def ticket_type_delete(interaction: discord.Interaction, name: str):
    conf = get_guild_conf(interaction.guild.id)

    if name not in conf["ticket_types"]:
        await interaction.response.send_message(
            f"❌ Nincs ilyen ticket típus: **{name}**",
            ephemeral=True
        )
        return

    conf["ticket_types"].pop(name)
    save_config(config)

    await interaction.response.send_message(
        f"🗑 Ticket típus törölve: **{name}**",
        ephemeral=True
    )

# -------- CLAIM --------
@bot.tree.command(name="ticket_claim", description="Ticket claimelése")
async def ticket_claim(interaction: discord.Interaction):
    conf = get_guild_conf(interaction.guild.id)
    cid = str(interaction.channel.id)

    if cid not in conf["open_tickets"]:
        await interaction.response.send_message(
            "❌ Ez nem ticket csatorna.",
            ephemeral=True
        )
        return

    conf["open_tickets"][cid]["claimed_by"] = interaction.user.id
    save_config(config)

    await interaction.response.send_message(
        f"✅ Ticket claimelve: {interaction.user.mention}"
    )

# -------- CLOSE --------
@bot.tree.command(name="ticket_close", description="Ticket bezárása")
async def ticket_close(interaction: discord.Interaction):
    conf = get_guild_conf(interaction.guild.id)
    cid = str(interaction.channel.id)

    if cid not in conf["open_tickets"]:
        await interaction.response.send_message(
            "❌ Ez nem ticket csatorna.",
            ephemeral=True
        )
        return

    log_id = conf.get("log_channel")
    if log_id:
        log_ch = interaction.guild.get_channel(log_id)
        if log_ch:
            await log_ch.send(
                f"🗑 Ticket zárva: {interaction.channel.name}"
            )

    conf["open_tickets"].pop(cid)
    save_config(config)

    await interaction.channel.delete()

# -------- LOG CHANNEL --------
@bot.tree.command(name="ticket_logchannel", description="Ticket log csatorna beállítása")
@app_commands.checks.has_permissions(manage_guild=True)
async def ticket_logchannel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    conf = get_guild_conf(interaction.guild.id)
    conf["log_channel"] = channel.id
    save_config(config)

    await interaction.response.send_message(
        f"✅ Log csatorna beállítva: {channel.mention}",
        ephemeral=True
    )

# ================== RUN ==================

bot.run(TOKEN)
