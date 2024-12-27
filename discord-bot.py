import os
from dotenv import load_dotenv
import json
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SERVER_NAME = os.getenv('SERVER_NAME')

intents = discord.Intents.default()
intents.members = True  # Enables the member events, including on_member_join
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

GUILD_ID = int(os.getenv('GUILD_ID')) 
INTRODUCTIONS_CHANNEL_ID = int(os.getenv('INTRODUCTIONS_CHANNEL_ID'))
MESSAGE_ID = int(os.getenv('MESSAGE_ID'))

# Dictionary to store emoji-role mappings for each server
server_mappings = {}

# Load mappings from a JSON file
def load_mappings():
    global server_mappings
    try:
        with open("server_mappings.json", "r") as file:
            server_mappings = json.load(file)
    except FileNotFoundError:
        server_mappings = {}

# Save mappings to a JSON file
def save_mappings():
    with open("server_mappings.json", "w") as file:
        json.dump(server_mappings, file, indent=4)

# Load mappings on bot startup
load_mappings()

# Command to add a new emoji-role mapping
@bot.tree.command(name="add_mapping", description="Add an emoji-role mapping")
@app_commands.default_permissions(manage_roles=True)
async def add_mapping(interaction: discord.Interaction, emoji: str, role_name: str):
    """Add an emoji-role mapping."""
    guild_id = str(interaction.guild_id)
    guild = interaction.guild
    role = discord.utils.get(guild.roles, name=role_name)

    if not role:
        await interaction.response.send_message(f"Role '{role_name}' does not exist.", ephemeral=True)
        return

    if guild_id not in server_mappings:
        server_mappings[guild_id] = {}
    server_mappings[guild_id][emoji] = role_name
    save_mappings()
    await interaction.response.send_message(f"Mapping added: {emoji} -> {role_name}", ephemeral=True)

@bot.tree.command(name="remove_mapping", description="Remove an emoji-role mapping")
@app_commands.default_permissions(manage_roles=True)
async def remove_mapping(interaction: discord.Interaction, emoji: str):
    """Remove an emoji-role mapping."""
    guild_id = str(interaction.guild_id)
    if guild_id in server_mappings and emoji in server_mappings[guild_id]:
        del server_mappings[guild_id][emoji]
        save_mappings()
        await interaction.response.send_message(f"Mapping removed for emoji: {emoji}", ephemeral=True)
    else:
        await interaction.response.send_message(f"No mapping found for emoji: {emoji}", ephemeral=True)

@bot.tree.command(name="setup_roles", description="Set up reactions for a message")
@app_commands.default_permissions(manage_roles=True)
async def setup_roles(interaction: discord.Interaction, message_id: int):
    """Set up reactions for a message based on mappings."""
    guild_id = str(interaction.guild_id)
    if guild_id not in server_mappings or not server_mappings[guild_id]:
        await interaction.response.send_message("No emoji-role mappings found.", ephemeral=True)
        return

    channel = interaction.channel
    message = await channel.fetch_message(message_id)
    for emoji in server_mappings[guild_id].keys():
        await message.add_reaction(emoji)

    await interaction.response.send_message("Reactions added!", ephemeral=True)

@bot.event
async def on_raw_reaction_add(payload):
    """Assign a role when a user reacts with a valid emoji."""
    guild_id = str(payload.guild_id)
    if guild_id not in server_mappings:
        return

    # Handle both custom and default emojis
    if payload.emoji.id:  # Custom emoji
        emoji_key = f"<:{payload.emoji.name}:{payload.emoji.id}>"
    else:  # Default emoji
        emoji_key = payload.emoji.name

    if emoji_key not in server_mappings[guild_id]:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    if not member:
        return

    role_name = server_mappings[guild_id][emoji_key]
    role = discord.utils.get(guild.roles, name=role_name)
    if role:
            await member.add_roles(role)
            try:
                embed = discord.Embed(
                    color=discord.Color.light_gray(),
                    description=f'✅ คุณได้รับ Role {role.name} บนเซิร์ฟเวอร์ {guild.name} เรียบร้อยแล้ว'
                )
                await member.send(embed=embed)
            except discord.Forbidden:
                print(f"Couldn't send DM to {member.name}")

@bot.event
async def on_raw_reaction_remove(payload):
    """Remove a role when a user removes a valid reaction."""
    guild_id = str(payload.guild_id)
    if guild_id not in server_mappings:
        return

    # Handle both custom and default emojis
    if payload.emoji.id:  # Custom emoji
        emoji_key = f"<:{payload.emoji.name}:{payload.emoji.id}>"
    else:  # Default emoji
        emoji_key = payload.emoji.name

    if emoji_key not in server_mappings[guild_id]:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    if not member:
        return

    role_name = server_mappings[guild_id][emoji_key]
    role = discord.utils.get(guild.roles, name=role_name)
    if role:
            await member.remove_roles(role)
            try:
                embed = discord.Embed(
                    color=discord.Color.light_gray(),
                    description=f':no_entry: คุณได้ปลด Role {role.name} บนเซิร์ฟเวอร์ {guild.name} เรียบร้อยแล้ว'
                )
                await member.send(embed=embed)
            except discord.Forbidden:
                print(f"Couldn't send DM to {member.name}")

# On Member Join
@bot.event
async def on_member_join(member):
    try:
        # Send a welcome message in the introductions channel visible only for a short time
        introductions_channel = bot.get_channel(INTRODUCTIONS_CHANNEL_ID)
        if introductions_channel:
            message = await introductions_channel.send(
                f"ยินดีตอนรับเข้าสู่ server, {member.mention}! โปรดพิมพ์ `/ind` เพื่อแนะนำตัวเอง"
            )
            # Delete the message after 10 seconds
            await message.delete(delay=10)
    except Exception as e:
        print(f"Error in on_member_join: {e}")
        
# Slash Command for Introduction
@bot.tree.command(name="ind", description="Introduce yourself")
async def ind(interaction: discord.Interaction):
    if interaction.channel.id != INTRODUCTIONS_CHANNEL_ID:
        await interaction.response.send_message(
            "โปรดใช้คำสั่งนี้ใน Introduction channel", ephemeral=True
        )
        return

    await interaction.response.send_message("บอทได้ทำการส่งข้อความไปยังแชทส่วนตัว", ephemeral=True)

    def check(m):
        return m.author == interaction.user and isinstance(m.channel, discord.DMChannel)

    try:
        # Collect user input via DMs
        await interaction.user.send("ชื่อเล่น ?")
        name_msg = await bot.wait_for('message', check=check, timeout=120)

        await interaction.user.send("เพศ ?")
        gender_msg = await bot.wait_for('message', check=check, timeout=120)

        await interaction.user.send("อื่น ๆ ?")
        other_msg = await bot.wait_for('message', check=check, timeout=120)

        name, gender, other_info = name_msg.content, gender_msg.content, other_msg.content
        utc_time = datetime.utcnow()
        thailand_time = utc_time + timedelta(hours=7)
        formatted_time = thailand_time.strftime('%m/%d/%Y %I:%M %p Thailand Time')

        # Prepare the introduction embed with proper formatting and profile image
        introduction_text = (
            "༶•┈┈⛧┈♛ ♛┈⛧┈┈•༶\n"
            f"**name** : {name}\n"
            f"**gender** : {gender}\n"
            f"**other** : {other_info}\n"
            "༶•┈┈⛧┈♛ ♛┈⛧┈┈•༶"
        )

        embed = discord.Embed(color=discord.Color.dark_gray())
        embed.set_author(name=f"{interaction.user.display_name}", icon_url=interaction.user.avatar.url)
        embed.set_thumbnail(url=interaction.user.avatar.url)  # Set thumbnail to profile image
        embed.add_field(name="Introduction", value=introduction_text, inline=False)
        embed.set_footer(text=f"ID: {interaction.user.id} • {formatted_time}")
        
        # Post introduction card in the introduction channel
        introductions_channel = bot.get_channel(INTRODUCTIONS_CHANNEL_ID)
        if introductions_channel:
            await introductions_channel.send(embed=embed)
        else:
            await interaction.response.send_message(
                "Introduction channel not found. Please contact an admin.", ephemeral=True
            )

    except discord.Forbidden:
        await interaction.response.send_message(
            "I cannot send you DMs. Please enable DMs from server members.", ephemeral=True
        )
    except Exception as e:
        await interaction.user.send(f"An error occurred: {e}")

bot.run(TOKEN)