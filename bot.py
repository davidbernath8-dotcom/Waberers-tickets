import discord
from discord.ext import commands
from discord import app_commands, ui, Embed, Colour
import json
import os

# ---------- Bot setup ----------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- Config ----------
CONFIG_FILE = "ticket_data.json"

COLOR_MAP = {
    "red": Colour.red(),
    "green": Colour.green(),
    "blue": Colour.blue(),
    "orange": Colour.orange(),
    "blurple": Colour.blurple()
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"ticket_types": {}, "counter": 1, "log_channel": None}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

guild_conf = load_config()

# ---------- Ticket Modal ----------
class TicketModal(ui.Modal):
    def __init__(self, ticket_type_name: str):
        super().__init__(title=f"Ticket: {ticket_type_name}")
        self.ticket_type_name = ticket_type_name

        type_conf = guild_conf["ticket_types"].get(ticket_type_name, {})
        questions = type_conf.get("questions", ["Írd le a problémát"])
        for q in questions:
            self.add_item(ui.InputText(label=q, style=discord.InputTextStyle.paragraph))

    async def on_submit(self, interaction: discord.Interaction):
        conf = guild_conf["ticket_types"][self.ticket_type_name]
        guild = interaction.guild

        counter = guild_conf.get("counter", 1)
        channel_name = f"{self.ticket_type_name}-{counter}"
        guild_conf["counter"] = counter + 1
        save_config(guild_conf)

        overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
        for role_id in conf.get("roles", []):
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True)
        overwrites[interaction.user] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        ticket_channel = await guild.create_text_channel(channel_name, overwrites=overwrites)

        color = COLOR_MAP.get(conf.get("color", "blurple"), Colour.blurple())
        embed = Embed(
            title=f"Ticket: {self.ticket_type_name}",
            description=f"{interaction.user.mention} létrehozott egy új ticketet.",
            color=color
        )

        for i, child in enumerate(self.children, start=1):
            embed.add_field(name=f"Kérdés {i}", value=child.value, inline=False)

        role_mentions = " ".join(f"<@&{r}>" for r in conf.get("roles", []))
        embed.add_field(name="Pingelve:", value=role_mentions or "Nincs", inline=False)

        await ticket_channel.send(embed=embed)

        log_channel_id = guild_conf.get("log_channel")
        if log_channel_id:
            log_channel = guild.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(f"Ticket létrehozva: {ticket_channel.mention} Nyitotta: {interaction.user.mention}")

        await interaction.response.send_message(f"Ticket létrehozva: {ticket_channel.mention}", ephemeral=True)

# ---------- Ticket Panel ----------
class TicketPanel(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for tname in guild_conf.get("ticket_types", {}):
            self.add_item(ui.Button(
                label=tname,
                style=discord.ButtonStyle.primary,
                custom_id=f"ticket_{tname}"
            ))

# ---------- Ready ----------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

# ---------- Ticket Commands ----------
@bot.tree.command(name="ticket_panel", description="Ticket panel küldése")
async def ticket_panel(interaction: discord.Interaction):
    view = TicketPanel()
    await interaction.response.send_message(
        "Válassz ticket típust a létrehozáshoz:",
        view=view,
        ephemeral=False
    )

@bot.tree.command(name="ticket_type_add", description="Új ticket típus hozzáadása")
@app_commands.describe(
    name="Ticket típusa",
    color="Embed színe (red, green, blue, orange, blurple)",
    roles="Pingelhető rangok ID, vesszővel elválasztva",
    questions="Kérdések típushoz, vesszővel elválasztva"
)
async def ticket_type_add(interaction: discord.Interaction, name: str, color: str, roles: str, questions: str):
    role_ids = [int(r.strip()) for r in roles.split(",")] if roles else []
    question_list = [q.strip() for q in questions.split(",")] if questions else ["Írd le a problémát"]
    guild_conf["ticket_types"][name] = {"roles": role_ids, "color": color.lower(), "questions": question_list}
    save_config(guild_conf)

    # Automatikusan küldjük a panelt
    view = TicketPanel()
    await interaction.response.send_message(
        f"Ticket típus hozzáadva: {name}\nPanel frissítve, kattints a gombra a ticket létrehozásához.",
        view=view,
        ephemeral=False
    )

@bot.tree.command(name="ticket_type_remove", description="Ticket típus törlése")
@app_commands.describe(name="Ticket típusa")
async def ticket_type_remove(interaction: discord.Interaction, name: str):
    if name in guild_conf["ticket_types"]:
        del guild_conf["ticket_types"][name]
        save_config(guild_conf)
        await interaction.response.send_message(f"Ticket típus törölve: {name}", ephemeral=True)
    else:
        await interaction.response.send_message("Ez a ticket típus nem létezik.", ephemeral=True)

@bot.tree.command(name="log_channel", description="Log csatorna beállítása")
@app_commands.describe(channel="Ticket log csatorna")
async def log_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_conf["log_channel"] = channel.id
    save_config(guild_conf)
    await interaction.response.send_message(f"Log csatorna beállítva: {channel.mention}", ephemeral=True)

# ---------- Claim / Close ----------
@bot.tree.command(name="ticket_claim", description="Ticketet claimelni")
async def ticket_claim(interaction: discord.Interaction):
    if not any(interaction.channel.name.startswith(k) for k in guild_conf.get("ticket_types", {})):
        await interaction.response.send_message("Ez nem ticket csatorna!", ephemeral=True)
        return
    await interaction.response.send_message(f"{interaction.user.mention} claimelte a ticketet.", ephemeral=False)

@bot.tree.command(name="ticket_close", description="Ticket bezárása")
@app_commands.describe(reason="Miért zárjuk be?")
async def ticket_close(interaction: discord.Interaction, reason: str):
    if not any(interaction.channel.name.startswith(k) for k in guild_conf.get("ticket_types", {})):
        await interaction.response.send_message("Ez nem ticket csatorna!", ephemeral=True)
        return

    log_channel_id = guild_conf.get("log_channel")
    if log_channel_id:
        log_channel = interaction.guild.get_channel(log_channel_id)
        if log_channel:
            await log_channel.send(f"Ticket zárva: {interaction.channel.mention} Zárta: {interaction.user.mention} | Indok: {reason}")

    await interaction.channel.delete()

# ---------- Button callback ----------
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get("custom_id")
        if custom_id and custom_id.startswith("ticket_"):
            ticket_type_name = custom_id.replace("ticket_", "")
            modal = TicketModal(ticket_type_name)
            await interaction.response.send_modal(modal)

# ---------- Run ----------
bot.run(os.getenv("TOKEN"))
