
import fnmatch
import sys
import nextcord as discord
import os
import sqlite3 as sql
import random
import gitignore_parser
import asyncio
from cogs.tickets import TicketView
from nextcord.ext import commands
from nextcord import SlashOption, Interaction
from nextcord.ext import application_checks
from github import Github, InputGitTreeElement
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env file

github_token = os.getenv("GITHUB_API_TOKEN")  
token = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.persistent_views_added = False

    async def on_ready(self):
        if not self.persistent_views_added:
            self.add_view(TicketView(tag=None))
            self.persistent_views_added = True

        print(f"Logged in as {self.user} (ID: {self.user.id})")


bot = Bot(command_prefix="q>", default_guild_ids=[1066316768093671514, 1096749115314028554], intents=intents)
code = ""
# load databases

with sql.connect('data/server_entries.db') as db: 
    db.execute('''CREATE TABLE IF NOT EXISTS help_entries
                (server_id TEXT, help_name TEXT, tag TEXT, answer TEXT, image TEXT)''')

with sql.connect('data/tickets_count.db') as db:
    db.execute('CREATE TABLE IF NOT EXISTS ticket_counts (server_id TEXT, last_ticket_number INTEGER)')

with sql.connect('data/ticketData.db') as db:
    db.execute('CREATE TABLE IF NOT EXISTS data (tag TEXT, server_id TEXT, ticket_id TEXT)')

# load cogs
try:
    for file in os.listdir('./cogs'):
        if file.endswith('.py'):
            bot.load_extension(f'cogs.{file[:-3]}')
except FileNotFoundError:
    print("The system cannot find the cogs folder. You most likely haven't created it, or the program does not have the permissions to access it.")




# owner commands:
@bot.slash_command(description="Reloads a cog.")
@application_checks.is_owner()
async def reload(interaction:Interaction, cog:str=SlashOption(required=True)):
    cog = cog.lower()
    try:
        bot.reload_extension(f"cogs.{cog}")
        await interaction.send(f"{cog} has been reloaded.", ephemeral=True)
    except commands.ExtensionNotLoaded:
        await interaction.send(f"{cog} is not currently loaded/does not exist", ephemeral=True)
    except Exception as error:
        await interaction.send(f"a fatal error occurred that was not handled correctly. log:\n{error}", ephemeral=True)
    

@bot.slash_command(description="Push local changes to GitHub.")
@application_checks.is_owner()
async def sync(interaction:Interaction):
    # Make sure to replace GITHUB_API_TOKEN in the .env with your personal access token
    g = Github(github_token)

    # Get the authenticated user
    user = g.get_user()

    repo = user.get_repo("Qubit")
    base_directory = "D:/Coding/Qubit/"
    await interaction.response.defer()

    # Parse the .gitignore file
    gitignore = []
    with open(".gitignore", "r") as file:
        gitignore = file.read().splitlines()

    # Loop through all the files and folders in the base directory and upload them to GitHub
    for root, dirs, files in os.walk(base_directory):
        # Upload the files to GitHub
        for filename in files:
            # Check if the file is ignored by .gitignore
            if any(fnmatch.fnmatch(filename, pattern) for pattern in gitignore):
                continue

            with open(os.path.join(root, filename), "r", encoding="utf-8") as file:
                content = file.read()
                path = os.path.relpath(os.path.join(root, filename), base_directory)
                print(filename)
                try:
                    # Get the current contents of the file on the branch
                    contents = repo.get_contents(path, ref="main")
                    # Update the file with the new content and sha value
                    repo.update_file(path, f"Update {filename}", content, contents.sha, branch="main")
                except Exception as e:
                    print(f"Failed to upload {filename}\n {e}")

        # Create the folders on GitHub
        for dirname in dirs:
            path = os.path.relpath(os.path.join(root, dirname), base_directory)
            print(dirname)
            try:
                repo.create_git_tree(
                    tree=[{"path": f"{path}/", "mode": "040000", "type": "tree"}],
                    base_tree=repo.get_branch("main").commit.commit.tree.sha,
                )
            except:
                print(f"Failed to create {dirname}")



@bot.slash_command(description="Unloads a cog.")
@application_checks.is_owner()
async def unload(interaction:Interaction, cog:str=SlashOption(required=True)):
    cog = cog.lower()
    try:
        bot.reload_extension(f"cogs.{cog}")
        await interaction.send(f"{cog} has been unloaded.", ephemeral=True)
    except commands.ExtensionNotFound:
        await interaction.send(f"{cog} does not exist.", ephemeral=True)
    except Exception as error:
        await interaction.send(f"a fatal error occurred that was not handled correctly. log:\n{error}", ephemeral=True)
    
@bot.slash_command(description="Shuts down the bot.")
@application_checks.is_owner()
async def shutdown(interaction:Interaction):
    global confirmation_code
    
    letters_numbers = "abcdefghijklmnopqrstuvwxyz0123456789"
    confirmation_code = "".join(random.choices(letters_numbers, k=4))
    
    await interaction.send(f"Are you sure you want to shut down the bot? Type `{confirmation_code}` to confirm.")
    
    # define a function to check if the user's message matches the confirmation code
    def check_message(message: discord.Message):
        if message.content == confirmation_code and message.author == interaction.user:
            return True
        else:
            pass
    try:
        # wait for the user to confirm with the code
        message = await bot.wait_for('message', check=check_message, timeout=8)
    except TimeoutError:
        # if the user doesn't confirm within 8 seconds, cancel the shutdown
        await interaction.send("Shutdown canceled. You took too long to confirm.")
    else:
        # if the confirmation code matches, shut down the bot
        await interaction.send("Shutting down...")
        await bot.close()

@bot.slash_command(description="Wipes all data in the entries database.")
@application_checks.is_owner()
async def wipe_data(interaction:Interaction):
    global confirmation_code
    
    letters_numbers = "abcdefghijklmnopqrstuvwxyz0123456789"
    confirmation_code = "".join(random.choices(letters_numbers, k=4))
    
    await interaction.send(f"Are you sure you want to wipe all data? Type `{confirmation_code}` to confirm.")
    
    # define a function to check if the user's message matches the confirmation code
    def check_message(message: discord.Message):
        if message.content == confirmation_code and message.author == interaction.user:
            return True
        else:
            pass
    try:
        # wait for the user to confirm with the code
        message = await bot.wait_for('message', check=check_message, timeout=8)
    except TimeoutError:
        # if the user doesn't confirm within 8 seconds, cancel the shutdown
        await interaction.send("Canceled. You took too long to confirm.")
    else:
        # if the confirmation code matches, shut down the bot
        await interaction.send("Wiping... (requires restart)")
        print("wiping data...")
        with open("data/server_entries.db", "w") as f:
            f.truncate(0)
        await asyncio.sleep(3)
        await interaction.send("All data wiped. Restarting...")
        def restart_program():
            python = sys.executable
            os.execl(python, python, *sys.argv)

        # call the restart function
        restart_program()



bot.run(token)