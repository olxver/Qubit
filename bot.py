
import sys
import nextcord as discord
import os
import sqlite3 as sql
import random
import asyncio
from nextcord.ext import commands
from nextcord import SlashOption, Interaction
from nextcord.ext import application_checks

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="q>", default_guild_ids=[1066316768093671514, 1096749115314028554], intents=intents)
code = ""
# create table if it doesnt exist:

with sql.connect('data/server_entries.db') as db: 
    db.execute('''CREATE TABLE IF NOT EXISTS help_entries
                (server_id TEXT, help_name TEXT, tag TEXT, answer TEXT, image TEXT)''')

# load cogs
try:
    for file in os.listdir('./cogs'):
        if file.endswith('.py'):
            bot.load_extension(f'cogs.{file[:-3]}')
except FileNotFoundError:
    print("The system cannot find the cogs folder. You most likely haven't created it, or the program does not have the permissions to access it.")

# run when bot is connected to discord
@bot.event
async def on_ready():
    print(f"connected to discord with id {bot.user.id} and user {bot.user}")


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



bot.run("token")