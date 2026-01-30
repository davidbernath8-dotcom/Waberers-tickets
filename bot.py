import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import json
import os

CONFIG_FILE = "ticket_config.json"

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
            "types": {},        # ticket típusok: {name: {"roles":[id,...], "color":"kek"}}
            "log_channel_id": None,
            "claims": {}        # channel_id : user_id
        }
        save_config(config)
    return config[gid]

# -------------------
# BOT INIT
# -------------------

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

# -------------------
# TICKET MODAL
# -------------------

class TicketModal(Modal):
    def __init__(self, ticket_type: str):
        super().__init__(title=f"{ticket_type} ticket")
        self.ticket_type = ticket_type
        self.indok = TextInput(label="Miért nyitsz ticketet?", style=discord.TextStyle.paragraph)
        self.add_item(self.indok)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        conf = get_guild_conf(guild.id)
        conf["counter"] += 1
        counter = conf["counter"]
        save_config(config)

        data = conf["types"].get(self.ticket_type)
        if not data:
            await interaction.response.send_message("❌ Ez a ticket típus már nem létezik.", ephemeral=True)
            return

        # Jogosultságok + role ping
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

        # Üzenet
        await channel.send(f"{' '.join(mentions)}\n🎫 {interaction.user.mention} nyitott egy ticketet\n**Ok:** {self.indok.value}")

        # Log
        log_id = conf.get("log_channel_id")
        if log_id:
            log_ch = guild.get_channel(log_id)
            if log_ch:
                await log_ch.send(f"🎫 Ticket nyitva: {channel.mention} | {interaction.user.mention} | típus: {self.ticket_type}")

        # Ephemeral válasz a nyitónak
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
            style = GOMB_SZINEK.get(data.get("color", "kek"), discord.ButtonStyle.primary)
            self.add_item(TicketButton(name, style))

# -------------------
# COMMANDS
# -------------------

@bot.tree.command(name="ticket_panel", description="Ticket panel küldése")
async def ticket_panel(interaction: discord.Interaction):
    await interaction.response.send_message("🎟 Válaszd ki a ticket típusát:", view=TicketPanel(interaction.guild.id))

@bot.tree.command(name="ticket_type", description="Új ticket típus létrehozása")
@app_commands.checks.has_permissions(manage_guild=True)
async def ticket_type(interaction: discord.Interaction, name: str, roles: str, color: str = "kek"):
    # roles: vesszővel elválasztott role ID-k
    role_ids = [int(r.strip()) for r in roles.split(",")]
    conf = get_guild_conf(interaction.guild.id)
    conf["types"][name] = {"roles": role_ids, "color": color}
    save_config(config)
    await interaction.response.send_message(f"✅ Ticket típus létrehozva: **{name}** | Roles: {roles} | Szín: {color}")

@bot.tree.command(name="ticket_addrole", description="Role hozzáadása ticket típushoz")
@app_commands.checks.has_permissions(manage_guild=True)
async def ticket_addrole(interaction: discord.Interaction, name: str, role_id: int):
    conf = get_guild_conf(interaction.guild.id)
    if name not in conf["types"]:
        await interaction.response.send_message("❌ Nincs ilyen ticket típus.", ephemeral=True)
        return
    if role_id not in conf["types"][name]["roles"]:
        conf["types"][name]["roles"].append(role_id)
        save_config(config)
    await interaction.response.send_message(f"➕ Role hozzáadva **{name}** tickethez")

@bot.tree.command(name="ticket_setcolor", description="Ticket gomb színének beállítása")
@app_commands.checks.has_permissions(manage_guild=True)
async def ticket_setcolor(interaction: discord.Interaction, name: str, color: str):
    if color not in GOMB_SZINEK:
        await interaction.response.send_message("❌ Színek: kek, zold, piros, szurke, narancs", ephemeral=True)
        return
    conf = get_guild_conf(interaction.guild.id)
    if name not in conf["types"]:
        await interaction.response.send_message("❌ Nincs ilyen ticket típus.", ephemeral=True)
        return
    conf["types"][name]["color"] = color
    save_config(config)
    await interaction.response.send_message(f"🎨 **{name}** színe beállítva: `{color}`")

@bot.tree.command(name="ticket_logchannel", description="Ticket log csatorna beállítása")
@app_commands.checks.has_permissions(manage_guild=True)
async def ticket_logchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    conf = get_guild_conf(interaction.guild.id)
    conf["log_channel_id"] = channel.id
    save_config(config)
    await interaction.response.send_message(f"✅ Log csatorna beállítva: {channel.mention}")

# -------------------
# /ticket_claim
# -------------------
@bot.tree.command(name="ticket_claim", description="Claimeld a ticketet")
async def ticket_claim(interaction: discord.Interaction):
    channel = interaction.channel
    conf = get_guild_conf(interaction.guild.id)
    ticket_types_lower = [t.lower() for t in conf["types"].keys()]
    if not any(channel.name.lower().startswith(t) for t in ticket_types_lower):
        await interaction.response.send_message("❌ Ez nem ticket csatorna.", ephemeral=True)
        return

    conf["claims"][str(channel.id)] = interaction.user.id
    save_config(config)
    await interaction.response.send_message(f"✅ {interaction.user.mention} claimelte a ticketet.")

# -------------------
# /ticket_close
# -------------------
@bot.tree.command(name="ticket_close", description="Bezárja a ticketet")
async def ticket_close(interaction: discord.Interaction):
    channel = interaction.channel
    conf = get_guild_conf(interaction.guild.id)
    ticket_types_lower = [t.lower() for t in conf["types"].keys()]
    if not any(channel.name.lower().startswith(t) for t in ticket_types_lower):
        await interaction.response.send_message("❌ Ez nem ticket csatorna.", ephemeral=True)
        return

    # Log
    log_id = conf.get("log_channel_id")
    claimed_user_id = conf["claims"].get(str(channel.id))
    claimed_user = interaction.guild.get_member(claimed_user_id) if claimed_user_id else None
    if log_id:
        log_ch = interaction.guild.get_channel(log_id)
        msg = f"✅ Ticket lezárva: {channel.mention}"
        if claimed_user:
            msg += f" | Claimelve: {claimed_user.mention}"
        if log_ch:
            await log_ch.send(msg)

    conf["claims"].pop(str(channel.id), None)
    save_config(config)
    await channel.delete()

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
