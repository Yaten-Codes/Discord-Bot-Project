import discord
import requests
import random
from bs4 import BeautifulSoup
from discord.ext import commands
import logging
import json
from datetime import datetime


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
lines_cache = {}
used_lines = []
server_settings = {}

#---------------------------------------------------------------------daily commands/total

# Define data structures
commands_stats = {
    "total_commands": 0,
    "server_stats": {}
}

#created a update user command so whenever a user uses a command it updates the user id and user name
# and total commands used by them in a json file called
#"user_commands.json for all users regardless of servers maybe you can nest the servers so it lists servers
#along with user names and ids
user_commands_stats = {}  # Initialize a dictionary to store user command stats
def update_user_commands(server_name, user_id, user_name):
    global user_commands_stats

    # Load existing user commands stats from file
    with open("user_commands.json", "r") as user_stats_file:
        user_commands_stats = json.load(user_stats_file)

    # Create a nested structure for user stats if needed
    if server_name not in user_commands_stats:
        user_commands_stats[server_name] = {}

    # Update user's command count within the server
    if user_id not in user_commands_stats[server_name]:
        user_commands_stats[server_name][user_id] = {
            "username": user_name,
            "commands_used": 1
        }
    else:
        # Always update the username, even if it hasn't changed
        user_commands_stats[server_name][user_id]["username"] = user_name
        user_commands_stats[server_name][user_id]["commands_used"] += 1

    # Save the updated user commands stats to file
    with open("user_commands.json", "w") as user_stats_file:
        json.dump(user_commands_stats, user_stats_file, indent=4)

def update_commands(server_id, user_id, user_name):  # Receive user_id as an argument
    global commands_stats

    try:
        # Attempt to load existing stats
        with open("user_commands.json", "r") as user_stats_file:
            user_commands_stats = json.load(user_stats_file)
    except FileNotFoundError:
        # Create an empty file if it doesn't exist
        with open("user_commands.json", "w") as user_stats_file:
            json.dump({}, user_stats_file)  # Write an empty dictionary

    # Update total commands
    commands_stats["total_commands"] += 1

    # Get server name first
    server = client.get_guild(int(server_id))
    server_name = server.name if server else "Unknown Server"

    # Update server-wise commands using server name
    if server_name not in commands_stats["server_stats"]:
        commands_stats["server_stats"][server_name] = 1
    else:
        commands_stats["server_stats"][server_name] += 1

    # Save the updated stats to file
    with open("commands_stats.json", "w") as stats_file:
        json.dump(commands_stats, stats_file, indent=4)

    # Update user commands separately
    update_user_commands(server_name, user_id, user_name)


#--------------------------------------------------------------------------------------------------

pickup_lines = {
    "cheesy": {"url": "https://gist.github.com/Yaten-Codes/4d83a4e6333acca0dc173acdc36145bf", "description": "Generates a cheesy pickup line."},
    "anime": {"url": "https://gist.github.com/Yaten-Codes/cb88e5f92c63ab720e528a63a976abfd","description": "Generates an anime pickup line."},
    "math": {"url": "https://gist.github.com/Yaten-Codes/68379844ad0e7dfea6cb005a21bbd3ad","description": "Generates a math pickup line."},
    "pokemon": {"url": "https://gist.github.com/Yaten-Codes/60562b7ddd4b793a55f5e6f5fe2cce64","description": "Generates a pokemon pickup line."},
    "poetic": {"url": "https://gist.github.com/Yaten-Codes/c4f52d54cb8ca5ffd35468f2a3086c56","description": "Generates a poetic pickup line."},
    "roast": {"url": "https://gist.github.com/Yaten-Codes/c38d10c0cbefed46b3b9b9425e95b079","description": "Generates a roast."},
    "joke": {"url": "https://gist.github.com/Yaten-Codes/9f43585afc6d891794c7e3f6cf21bdfb","description": "Generates a joke."},

}

intents = discord.Intents.default()
client = commands.Bot(command_prefix="!", intents=intents)



# Load server/channel mappings from a JSON file
def load_server_channel_mappings():
    try:
        with open("server_mappings.json", "r") as file:  # Using `open` correctly
            return json.load(file)
    except FileNotFoundError:
        return {}

# Save server/channel mappings to a JSON file
# Save server/channel mappings to a JSON file
def save_server_channel_mappings(mappings, guild):
    # Load existing mappings (if any)
    try:
        existing_data = load_server_channel_mappings()
    except FileNotFoundError:
        existing_data = {}

    # Merge new mappings with existing ones
    new_mappings = {}
    for server_id, channel_data in mappings.items():
        if server_id in existing_data:
            new_mappings[server_id] = {  # Update existing structure directly
                "channel_id": channel_data["channel_id"],  # Corrected structure
                "server_name": existing_data[server_id]["server_name"]  # Preserve server_name
            }
        else:
            new_mappings[server_id] = {
                "channel_id": channel_data["channel_id"],
                "server_name": guild.name  # Include server name for new mappings
            }

    # Save the combined mappings in the desired format
    with open("server_mappings.json", "w") as file:
        json.dump(new_mappings, file, indent=4)


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    print(f"Ready to serve in {len(client.guilds)} server(s).")
    await client.tree.sync()
    print('Logged in as {0.user}'.format(client))
    await client.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=f"{len(client.guilds)} servers"))

    # Get the server/channel mappings
    server_channel_mappings = load_server_channel_mappings()

    # Iterate over each server the bot is connected to
    for guild in client.guilds:
        # Get the channel ID for this server from the mappings, or choose a suitable one
        channel_data = server_channel_mappings.get(str(guild.id))

        if not channel_data:
            # Find a suitable channel based on permissions and visibility
            channel = None
            for text_channel in guild.text_channels:
                permissions = text_channel.permissions_for(guild.me)

                if permissions.send_messages and not permissions.view_channel:  # Prioritize visible channels
                    continue

                if permissions.send_messages and text_channel.name.lower() == "general":  # Prioritize general channels
                    channel = text_channel
                    break

                if permissions.send_messages and not channel:  # Fallback to any channel with send permissions
                    channel = text_channel

            if channel:
                channel_id = str(channel.id)
                # Store server name along with ID and channel ID
                server_channel_mappings[str(guild.id)] = {
                    "channel_id": channel_id,
                    "server_name": guild.name
                }
                save_server_channel_mappings(server_channel_mappings, guild)
            else:
                print(f"No suitable text channels found in server {guild.name}. Unable to send online message.")
                continue

        # Send the online message to the selected channel
        channel_data = server_channel_mappings.get(str(guild.id))

        if channel_data is not None:
            if isinstance(channel_data, dict):
                # If channel_data is a dictionary, get the 'channel_id' attribute
                channel_id = channel_data.get("channel_id", None)

                if channel_id is not None:
                    channel = client.get_channel(int(channel_id))  # line 106

                    if channel:
                        await channel.send("The bot is now online in this server.")
                    else:
                        print(f"Channel with ID {channel_id} not found. Unable to send online message.")
                else:
                    print("No 'channel_id' attribute found in channel_data.")
            else:
                print("channel_data is not a dictionary.")
        else:
            print("channel_data is None. Unable to send online message.")


@client.event
async def on_guild_join(guild):
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{len(client.guilds)} servers"))

@client.event
async def on_guild_remove(guild):
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{len(client.guilds)} servers"))


#this is an example of one of my commands
@client.tree.command(name="help", description="opens the list of commands")
async def help(interaction: discord.Interaction):
    open_message = "Available slash commands:\n"
    for command, data in pickup_lines.items():
        open_message += f"{command}: {data['description']}\n"
    await interaction.response.send_message(open_message)
    server_id = str(interaction.guild.id)  # Get server ID
    user_id = str(interaction.user.id)  # Obtain user ID
    user_name = interaction.user.display_name  #obtain User_name
    update_commands(server_id, user_id, user_name)



@client.tree.command(name="cheesy", description="Generates a cheesy pickup line")
async def cheesy(interaction: discord.Interaction, user: discord.Member = None):
    try:
        server_id = interaction.guild.id
        repeats_enabled = await check_repeats_enabled(server_id)
        pickup_line = await generate_pickup_line(interaction=interaction, category="cheesy", server_id=server_id)
        if user:
            pickup_line = f"{user.mention}, {pickup_line}"
        await interaction.response.send_message(pickup_line)
        user_id = str(interaction.user.id)  # Obtain user ID
        user_name = interaction.user.display_name
        update_commands(server_id, user_id, user_name)
    except KeyError as e:
        print(f"An error occurred: {e}")
        await interaction.response.send_message("An error occurred while generating the joke.")


@client.tree.command(name="anime", description="Generates a anime pickup line")
async def anime(interaction: discord.Interaction, user: discord.Member = None):
    try:
        server_id = interaction.guild.id
        repeats_enabled = await check_repeats_enabled(server_id)
        pickup_line = await generate_pickup_line(interaction=interaction, category="anime", server_id=server_id)
        if user:
            pickup_line = f"{user.mention}, {pickup_line}"
        await interaction.response.send_message(pickup_line)
        server_id = str(interaction.guild.id)  # Get server ID
        user_id = str(interaction.user.id)  # Obtain user ID
        user_name = interaction.user.display_name  # obtain User_name
        update_commands(server_id, user_id, user_name)
    except KeyError as e:
        print(f"An error occurred: {e}")
        await interaction.response.send_message("An error occurred while generating the joke.")



@client.tree.command(name="math", description="Generates a math pickup line")
async def math(interaction: discord.Interaction, user: discord.Member = None):
    try:
        server_id = interaction.guild.id
        repeats_enabled = await check_repeats_enabled(server_id)
        pickup_line = await generate_pickup_line(interaction=interaction, category="math", server_id=server_id)
        if user:
            pickup_line = f"{user.mention}, {pickup_line}"
        await interaction.response.send_message(pickup_line)
        server_id = str(interaction.guild.id)  # Get server ID
        user_id = str(interaction.user.id)  # Obtain user ID
        user_name = interaction.user.display_name  # obtain User_name
        update_commands(server_id, user_id, user_name)
    except KeyError as e:
        print(f"An error occurred: {e}")
        await interaction.response.send_message("An error occurred while generating the joke.")


@client.tree.command(name="pokemon", description="Generates a pokemon pickup line")
async def pokemon(interaction: discord.Interaction, user: discord.Member = None):
    try:
        server_id = interaction.guild.id
        repeats_enabled = await check_repeats_enabled(server_id)
        pickup_line = await generate_pickup_line(interaction=interaction, category="pokemon", server_id=server_id)
        if user:
            pickup_line = f"{user.mention}, {pickup_line}"
        await interaction.response.send_message(pickup_line)
        server_id = str(interaction.guild.id)  # Get server ID
        user_id = str(interaction.user.id)  # Obtain user ID
        user_name = interaction.user.display_name  # obtain User_name
        update_commands(server_id, user_id, user_name)
    except KeyError as e:
        print(f"An error occurred: {e}")
        await interaction.response.send_message("An error occurred while generating the joke.")


@client.tree.command(name="poetic", description="Generates a poetic pickup line")
async def poetic(interaction: discord.Interaction, user: discord.Member = None):
    try:
        server_id = interaction.guild.id
        repeats_enabled = await check_repeats_enabled(server_id)
        pickup_line = await generate_pickup_line(interaction=interaction, category="poetic", server_id=server_id)
        if user:
            pickup_line = f"{user.mention}, {pickup_line}"
        await interaction.response.send_message(pickup_line)
        server_id = str(interaction.guild.id)  # Get server ID
        user_id = str(interaction.user.id)  # Obtain user ID
        user_name = interaction.user.display_name  # obtain User_name
        update_commands(server_id, user_id, user_name)
    except KeyError as e:
        print(f"An error occurred: {e}")
        await interaction.response.send_message("An error occurred while generating the joke.")


@client.tree.command(name="roast", description="Generates a roast")
async def roast(interaction: discord.Interaction, user: discord.Member = None):
    try:
        server_id = interaction.guild.id
        repeats_enabled = await check_repeats_enabled(server_id)
        pickup_line = await generate_pickup_line(interaction=interaction, category="roast", server_id=server_id)
        if user:
            pickup_line = f"{user.mention}, {pickup_line}"
        await interaction.response.send_message(pickup_line)
        server_id = str(interaction.guild.id)  # Get server ID
        user_id = str(interaction.user.id)  # Obtain user ID
        user_name = interaction.user.display_name  # obtain User_name
        update_commands(server_id, user_id, user_name)
    except KeyError as e:
        print(f"An error occurred: {e}")
        await interaction.response.send_message("An error occurred while generating the joke.")





@client.tree.command(name="joke", description="Generates a joke")
async def joke(interaction: discord.Interaction, user: discord.Member = None):
    try:
        server_id = interaction.guild.id
        repeats_enabled = await check_repeats_enabled(server_id)
        pickup_line = await generate_pickup_line(interaction=interaction, category="joke", server_id=server_id)
        if user:
            pickup_line = f"{user.mention}, {pickup_line}"
        await interaction.response.send_message(pickup_line)
        server_id = str(interaction.guild.id)  # Get server ID
        user_id = str(interaction.user.id)  # Obtain user ID
        user_name = interaction.user.display_name  # obtain User_name
        update_commands(server_id, user_id, user_name)
    except KeyError as e:
        print(f"An error occurred: {e}")
        await interaction.response.send_message("An error occurred while generating the joke.")

0

@client.tree.command(name="enable_repeats", description="allows repeated pickup lines (not working properly yet)")
async def repeats(interaction:discord.Interaction):
        print("repeats enabled")
        server_id = str(interaction.guild.id)
        global server_settings
        if server_id not in server_settings:
            server_settings[server_id] = {"repeats_enabled": True}
        elif server_settings[server_id]["repeats_enabled"]:
            await interaction.response.send_message("Repeated pickup lines are already enabled.")
            return
        server_settings[server_id]["repeats_enabled"] = True
        global used_lines
        used_lines = {}
        await interaction.response.send_message("Repeated pickup lines enabled.")

@client.tree.command(name="disable_repeats", description="does not allow repeated pickup lines (not working properly yet)")
async def disable(interaction:discord.Interaction):
    print("Disable repeated pickup lines.")
    server_id = str(interaction.guild.id)
    global server_settings
    if server_id not in server_settings:
        server_settings[server_id] = {"repeats_enabled": True}
    elif not server_settings[server_id]["repeats_enabled"]:
        await interaction.response.send_message("Repeated pickup lines are already disabled.")
    else:
        server_settings[server_id]["repeats_enabled"] = False
        await interaction.response.send_message("Repeated pickup lines disabled.")
        print("Response sent successfully.")

async def check_repeats_enabled(server_id: str):
    global server_settings

    if server_id not in server_settings:
        server_settings[server_id] = {"repeats_enabled": True}

    return server_settings[server_id]["repeats_enabled"]




def pickupline_scrape(category):
    global used_lines
    if category not in lines_cache:
        lines = []
        url = pickup_lines[category]["url"]
        logging.info(f"Scraping pickup lines from URL: {url}")
        response = requests.get(url)
        if response.status_code == 200:
            logging.info(f"Received response from website: {response.text}")
            soup = BeautifulSoup(response.text, "html.parser")
            for td in soup.find_all("td"):
                line = td.text.strip()
                logging.info(f"Found pickup line: {line}")
                if line:
                    lines.append(line)
        else:
            logging.error(f"Failed to scrape pickup lines: received status code {response.status_code} from website")
        lines_cache[category] = lines
    return lines_cache[category]



async def generate_pickup_line(*, interaction=None, name=None, server_id=None, user=None, mentioned_user=None, category=None):
    global used_lines

    if not category:
        category = random.choice(list(pickup_lines.keys()))
    if category not in pickup_lines:
        raise ValueError("Invalid category")
    lines = pickupline_scrape(category)

    if category in ["enable_repeats", "disable_repeats"]:
        if category == "enable_repeats":
            await check_repeats_enabled(server_id)
            used_lines = []
            await interaction.response.send_message("Repeated pickup lines enabled.")
        else:
            server_settings[server_id]["repeats_enabled"] = False
            await interaction.response.send_message("Repeated pickup lines disabled.")
        return

    repeats_enabled = await check_repeats_enabled(server_id)

    if not repeats_enabled and category in used_lines:
        available_lines = list(set(lines) - set(used_lines))
        if not available_lines:
            used_lines = []
            await interaction.response.send_message("All lines have been used. Lines reset.")
            available_lines = lines
        pickup_line = random.choice(available_lines)
    else:
        pickup_line = random.choice(lines)

    used_lines.append(pickup_line)



    if interaction and mentioned_user:
        pickup_line = f"{mentioned_user.mention}, {pickup_line}"

    if name:
        pickup_line = pickup_line.replace("{name}", name)

    return pickup_line



# client.run("discord token")


























