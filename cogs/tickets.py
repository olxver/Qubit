import nextcord as discord
import os
import sqlite3 as sql
import random
import aiohttp
import io
import asyncio
from nextcord.ext import commands
from nextcord.ext.commands import cooldown, BucketType
from nextcord import SlashOption, Interaction
from nextcord.ext import application_checks



class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @discord.slash_command(description="Parent command for tickets")
    @commands.has_guild_permissions(manage_messages=True)
    @commands.cooldown(1, 10, BucketType.guild)
    async def tickets(self, interaction:Interaction):
        pass

    @tickets.subcommand(description="Create a message in which a user can create a ticket, with buttons")
    @commands.has_guild_permissions(manage_messages=True)
    @commands.cooldown(1, 10, BucketType.guild)
    async def create(self, interaction:Interaction, 
                    name:str=SlashOption(description="The name to display for the button?", required=True),
                    ticket_name=SlashOption(description="Do you want the name to count up based on the amount of tickets created or based on the users name?", choices={"count up", "user's name"}, required=True),
                    desc:str=SlashOption(description="The description for the embed? (add imgur source links if you want e.g i.imgur.com/example.png)", required=False)):

        
        await interaction.send(f"{name},{desc},{ticket_name}")




def setup(bot):
    bot.add_cog(Tickets(bot))
    print("Tickets cog loaded")