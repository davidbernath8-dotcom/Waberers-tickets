import discord
from discord.ext import commands
from discord import app_commands
import json
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "ticket_data.json"

# ---------------- DATA ----------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf8") as f:
        json.dump(data, f, indent=4)

# ---------------- MODAL ----------------

class TicketModal(discord.ui.Modal):
    def __init__(self, ticket_type, questions):
        super().__init__(title=f"{ticket_type} Ticket")
        self.ticket_type = ticket_type
        self.questions = questions
        self.answers = []

        for q in questions:
            self.add_item(discord.ui.TextInput(label=q, style=discord.TextStyle.paragraph))

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        guild_data = data[str(interaction.guild.id)]
        tdata = guild_data["types"][self.ticket_type]

        category = interaction.guild.get_channel(tdata["category"])
        role = interaction.guild.get_role(tdata["role"])

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        channel = await interaction.guild.create_text_channel(
            name=f"{self.ticket_type}-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title=f"{self.ticket_type} Ticket",
            color=tdata["color"]
        )

        for item in self.children:
            embed.add_field(name=item.label, value=item.value, inline=False)

        view = TicketButtons()

        await channel.send(interaction.user.mention, embed=embed, view=view)
        await interaction.response.send_message("Ticket létrehozva!", ephemeral=True)

# ---------------- BUTTONS ----------------

class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary, custom_id="claim_btn")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"{interaction.user.mention} claimelte a ticketet.", ephemeral=False)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="close_btn")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CloseModal())

# ---------------- CLOSE MODAL ----------------

class CloseModal(discord.ui.Modal, title="Ticket lezárása"):
    reason = discord.ui.TextInput(label="Miért zárod?", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        guild_data = data[str(interaction.guild.id)]
        log_channel = interaction.guild.get_channel(guild_data["log_channel"])

        embed = discord.Embed(title="Ticket lezárva", color=discord.Color.red())
        embed.add_field(name="Ticket", value=interaction.channel.name)
        embed.add_field(name="Lezárta", value=interaction.user.mention)
        embed.add_field(name="Ok", value=self.reason.value)

        await log_channel.send(embed=embed)

        await interaction.response.send_message("Ticket zárva...", ephemeral=True)
        await interaction.channel.delete()

# ---------------- PANEL ----------------

class PanelView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        data = load_data()
        types = data[str(guild_id)]["types"]

        for t in types:
            self.add_item(TicketButton(t))

class TicketButton(discord.ui.Button):
    def __init__(self, ticket_type):
        super().__init__(label=ticket_type, style=discord.ButtonStyle.secondary, custom_id=f"ticket_{ticket_type}")
        self.ticket_type = ticket_type

    async def callback(self, interaction: discord.Interaction):
        data = load_data()
        questions = data[str(interaction.guild.id)]["types"][self.ticket_type]["questions"]
        await interaction.response.send_modal(TicketModal(self.ticket_type, questions))

# ---------------- COMMANDS ----------------

@bot.tree.command(description="Ticket panel létrehozása")
async def panel(interaction: discord.Interaction):
    data = load_data()
    embed = discord.Embed(title="Ticket Panel", description="Válassz ticket típust")
    view = PanelView(interaction.guild.id)
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("Panel elküldve!", ephemeral=True)

@bot.tree.command(description="Ticket típus létrehozása")
@app_commands.describe(
    name="Ticket típus neve",
    category="Kategória ID",
    role="Support Role",
    color="Embed szín HEX (pl FF0000)",
    questions="Kérdések | jellel elválasztva"
)
async def add_type(interaction: discord.Interaction, name: str, category: discord.CategoryChannel, role: discord.Role, color: str, questions: str):
    data = load_data()
    gid = str(interaction.guild.id)

    if gid not in data:
        data[gid] = {"types": {}, "log_channel": None}

    data[gid]["types"][name] = {
        "category": category.id,
        "role": role.id,
        "color": int(color, 16),
        "questions": questions.split("|")
    }

    save_data(data)
    await interaction.response.send_message("Ticket típus létrehozva!")

@bot.tree.command(description="Ticket típus törlése")
async def delete_type(interaction: discord.Interaction, name: str):
    data = load_data()
    gid = str(interaction.guild.id)

    if name in data[gid]["types"]:
        del data[gid]["types"][name]
        save_data(data)
        await interaction.response.send_message("Ticket típus törölve.")
    else:
        await interaction.response.send_message("Nincs ilyen típus.")

@bot.tree.command(description="Log channel beállítása")
async def set_log(interaction: discord.Interaction, channel: discord.TextChannel):
    data = load_data()
    gid = str(interaction.guild.id)

    if gid not in data:
        data[gid] = {"types": {}, "log_channel": None}

    data[gid]["log_channel"] = channel.id
    save_data(data)

    await interaction.response.send_message("Log channel beállítva.")

# ---------------- READY ----------------

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot online: {bot.user}")

bot.run(os.getenv("TOKEN"))
