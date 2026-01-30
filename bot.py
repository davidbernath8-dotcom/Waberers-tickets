import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import json
import os

CONFIG_FILE = "ticket_config.json"

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

def get_guild_conf(guild_id: int):
    gid = str(guild_id)
    if gid not in config:
        config[gid] = {
            "counter": 0,
            "types": {},          # ticket types
            "log_channel_id": None,
            "open_tickets": {},  # channel_id: type
            "claims": {}         # channel_id: user_id
        }
        save_config(config)
    return config[gid]

# ================= BOT =================

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

GOMB_SZINEK = {
    "kek": discord.ButtonStyle.primary,
    "zold": discord.ButtonStyle.success,
    "piros": discord.ButtonStyle.danger,
    "szurke": discord.ButtonStyle.secondary,
    "narancs": discord.ButtonStyle.secondary
}

# ================= MODAL =================

class TicketModal(Modal):
    def __init__(self, ticket_type: str):
        super().__init__(title=f"{ticket_type} ticket")
        self.ticket_type = ticket_type
        self.reason = TextInput(label="Miért nyitsz ticketet?", style=discord.TextStyle.paragraph)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        conf = get_guild_conf(guild.id)

        conf["counter"] += 1
        counter = conf["counter"]

        data = conf["types"].get(self.ticket_type)
        if not data:
            await interaction.response.send_message("❌ Ticket típus nem létezik.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        mentions = []
        for rid in data["roles"]:
            role = guild.get_role(rid)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
                mentions.append(role.mention)

        channel_name = f"{self.ticket_type}-{counter}".replace(" ", "-").lower()
        channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)

        conf["open_tickets"][str(channel.id)] = self.ticket_type
        save_config(config)

        await channel.send(
            f"{' '.join(mentions)}\n🎫 {interaction.user.mention} ticketet nyitott\n**Ok:** {self.reason.value}"
        )

        log_id = conf.get("log_channel_id")
        if log_id:
            log_ch = guild.get_channel(log_id)
            if log_ch:
                await log_ch.send(
                    f"🎫 Ticket nyitva | {channel.mention} | {interaction.user.mention} | típus: {self.ticket_type}"
                )

        await interaction.response.send_message(f"✅ Ticket létrehozva: {channel.mention}", ephemeral=True)

# ================= PANEL =================

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
            style = GOMB_SZINEK.get(data.get("color", "kek"), discord.ButtonStyle.primary)
            self.add_item(TicketButton(name, style))

# ================= COMMANDS =================

@bot.tree.command(name="panel", description="Ticket panel megjelenítése")
async def panel(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🎟 Válaszd ki a ticket típusát:",
        view=TicketPanel(interaction.guild.id)
    )

@bot.tree.command(name="ticket_type", description="Új ticket típus létrehozása")
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
            "❌ Hibás role ID formátum. Vesszővel elválasztott számokat adj meg.",
            ephemeral=True
        )
        return

    if color not in GOMB_SZINEK:
        await interaction.response.send_message(
            "❌ Színek: kek, zold, piros, szurke, narancs",
            ephemeral=True
        )
        return

    conf = get_guild_conf(interaction.guild.id)
    conf["types"][name] = {
        "roles": role_ids,
        "color": color
    }
    save_config(config)

    await interaction.response.send_message(
        f"✅ Ticket típus létrehozva: **{name}**",
        ephemeral=True
    )

@bot.tree.command(name="ticket_logchannel", description="Ticket log csatorna beállítása")
@app_commands.checks.has_permissions(manage_guild=True)
async def ticket_logchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    conf = get_guild_conf(interaction.guild.id)
    conf["log_channel_id"] = channel.id
    save_config(config)
    await interaction.response.send_message(f"✅ Log csatorna: {channel.mention}")

@bot.tree.command(name="ticket_claim", description="Ticket claimelése")
async def ticket_claim(interaction: discord.Interaction):
    conf = get_guild_conf(interaction.guild.id)
    cid = str(interaction.channel.id)

    if cid not in conf["open_tickets"]:
        await interaction.response.send_message("❌ Ez nem ticket csatorna.", ephemeral=True)
        return

    conf["claims"][cid] = interaction.user.id
    save_config(config)

    await interaction.response.send_message(f"✅ {interaction.user.mention} claimelte a ticketet.")

@bot.tree.command(name="ticket_close", description="Ticket lezárása")
async def ticket_close(interaction: discord.Interaction):
    conf = get_guild_conf(interaction.guild.id)
    cid = str(interaction.channel.id)

    if cid not in conf["open_tickets"]:
        await interaction.response.send_message("❌ Ez nem ticket csatorna.", ephemeral=True)
        return

    log_id = conf.get("log_channel_id")
    if log_id:
        log_ch = interaction.guild.get_channel(log_id)
        if log_ch:
            await log_ch.send(f"🔒 Ticket lezárva: {interaction.channel.name}")

    conf["open_tickets"].pop(cid)
    conf["claims"].pop(cid, None)
    save_config(config)

    await interaction.channel.delete()

# ================= READY =================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot ONLINE | {len(bot.guilds)} szerver")

# ================= RUN =================

if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"))
