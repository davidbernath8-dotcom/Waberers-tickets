import discord
from discord.ext import commands
from discord import app_commands
import json
import os

TOKEN = os.getenv("TOKEN")
CONFIG_FILE = "ticket_config.json"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= CONFIG =================

def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf8") as f:
            return json.load(f)
    except:
        return {}

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf8") as f:
        json.dump(data, f, indent=2)

def get_guild_config(guild_id):
    data = load_config()
    if str(guild_id) not in data:
        data[str(guild_id)] = {
            "ticket_types": {},
            "log_channel": None
        }
        save_config(data)
    return data[str(guild_id)]

def set_guild_config(guild_id, cfg):
    data = load_config()
    data[str(guild_id)] = cfg
    save_config(data)

# ================= MODALS =================

class TicketModal(discord.ui.Modal):

    def __init__(self, ticket_name, questions, color):
        super().__init__(title=f"{ticket_name} Ticket")
        self.ticket_name = ticket_name
        self.questions = questions
        self.color = color
        self.inputs = []

        for q in questions[:5]:
            inp = discord.ui.TextInput(
                label=q,
                style=discord.TextStyle.paragraph,
                required=True
            )
            self.add_item(inp)
            self.inputs.append(inp)

    async def on_submit(self, interaction: discord.Interaction):

        guild = interaction.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            overwrites=overwrites
        )

        desc = ""
        for inp in self.inputs:
            desc += f"**{inp.label}**\n{inp.value}\n\n"

        embed = discord.Embed(
            title=f"{self.ticket_name} Ticket",
            description=desc,
            color=int(self.color.replace("#",""), 16)
        )

        view = TicketManageView(interaction.user.id)

        msg = await channel.send(
            content=interaction.user.mention,
            embed=embed,
            view=view
        )

        await interaction.response.send_message(
            f"Ticket létrehozva: {channel.mention}",
            ephemeral=True
        )

# ===== CLOSE MODAL =====

class CloseReasonModal(discord.ui.Modal, title="Ticket zárás oka"):

    def __init__(self, ticket_owner_id):
        super().__init__()
        self.ticket_owner_id = ticket_owner_id

        self.reason = discord.ui.TextInput(
            label="Miért zárod?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):

        cfg = get_guild_config(interaction.guild.id)
        log_id = cfg.get("log_channel")

        if log_id:
            log_channel = interaction.guild.get_channel(log_id)
            if log_channel:

                embed = discord.Embed(
                    title="🔒 Ticket lezárva",
                    color=discord.Color.red()
                )

                embed.add_field(
                    name="Zárta",
                    value=interaction.user.mention,
                    inline=True
                )

                embed.add_field(
                    name="Indok",
                    value=self.reason.value,
                    inline=False
                )

                embed.add_field(
                    name="Ticket csatorna",
                    value=interaction.channel.name,
                    inline=False
                )

                if self.ticket_owner_id:
                    owner = interaction.guild.get_member(self.ticket_owner_id)
                    if owner:
                        embed.add_field(
                            name="Ticket tulaj",
                            value=owner.mention,
                            inline=True
                        )

                await log_channel.send(embed=embed)

        await interaction.response.send_message("Ticket zárás...", ephemeral=True)
        await interaction.channel.delete(delay=3)

# ================= BUTTON VIEWS =================

class TicketPanelView(discord.ui.View):

    def __init__(self, guild_id):
        super().__init__(timeout=None)

        cfg = get_guild_config(guild_id)

        for name, data in cfg["ticket_types"].items():
            self.add_item(TicketOpenButton(name, data["questions"], data["color"]))

class TicketOpenButton(discord.ui.Button):

    def __init__(self, name, questions, color):
        super().__init__(label=name, style=discord.ButtonStyle.primary)
        self.ticket_name = name
        self.questions = questions
        self.color = color

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            TicketModal(self.ticket_name, self.questions, self.color)
        )

# ===== MANAGE =====

class TicketManageView(discord.ui.View):

    def __init__(self, owner_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.send(f"🎯 Claimelte: {interaction.user.mention}")
        await interaction.response.defer()

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            CloseReasonModal(self.owner_id)
        )

# ================= COMMANDS =================

@bot.tree.command(name="ticket_add_type")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_add_type(interaction: discord.Interaction, name: str, color: str, questions: str):

    cfg = get_guild_config(interaction.guild.id)

    cfg["ticket_types"][name] = {
        "color": color,
        "questions": questions.split("|")
    }

    set_guild_config(interaction.guild.id, cfg)

    await interaction.response.send_message(f"✅ Létrehozva: {name}", ephemeral=True)

@bot.tree.command(name="ticket_delete_type")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_delete_type(interaction: discord.Interaction, name: str):

    cfg = get_guild_config(interaction.guild.id)

    if name not in cfg["ticket_types"]:
        return await interaction.response.send_message("Nincs ilyen típus.", ephemeral=True)

    del cfg["ticket_types"][name]
    set_guild_config(interaction.guild.id, cfg)

    await interaction.response.send_message(f"🗑️ Törölve: {name}", ephemeral=True)

# ===== LOG CHANNEL =====

@bot.tree.command(name="ticket_set_log")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_set_log(interaction: discord.Interaction, channel: discord.TextChannel):

    cfg = get_guild_config(interaction.guild.id)
    cfg["log_channel"] = channel.id
    set_guild_config(interaction.guild.id, cfg)

    await interaction.response.send_message(
        f"📜 Log channel beállítva: {channel.mention}",
        ephemeral=True
    )

# ===== PANEL =====

@bot.tree.command(name="ticket_panel")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_panel(interaction: discord.Interaction):

    view = TicketPanelView(interaction.guild.id)

    embed = discord.Embed(
        title="🎫 Ticket Panel",
        description="Válassz ticket típust"
    )

    await interaction.response.send_message(embed=embed, view=view)
	
# ================= teszt parancs =================
# @bot.tree.command(name="invite")


# ================= READY =================


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot online: {bot.user}")

# ================= RUN =================

bot.run(TOKEN)
