import discord, asyncio
import scraper
import os, sys, json
import urllib.parse
import datetime
from dotenv import load_dotenv
import json

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
NEW_POSTINGS_CHANNEL_ID = int(os.getenv('NEW_POSTINGS_CHANNEL_ID'))
TESTING_CHANNEL_ID = int(os.getenv('TESTING_CHANNEL_ID'))
COMPANIES_CHANNEL_ID = int(os.getenv('COMPANIES_CHANNEL_ID'))

# Instantiated after bot is logged in
NEW_POSTINGS_CHANNEL = None
TESTING_CHANNEL = None
COMPANIES_CHANNEL = None

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

    global NEW_POSTINGS_CHANNEL, TESTING_CHANNEL, COMPANIES_CHANNEL
    NEW_POSTINGS_CHANNEL = bot.get_channel(NEW_POSTINGS_CHANNEL_ID)
    TESTING_CHANNEL = bot.get_channel(TESTING_CHANNEL_ID)
    COMPANIES_CHANNEL = bot.get_channel(COMPANIES_CHANNEL_ID)

    await get_new_roles_postings_task()

@bot.event
async def on_message(message):
    def add_to_blacklist(companies):
        config = get_config()
        blacklist = set(config["blacklist"])

        for company in companies:
            blacklist.add(company)

        s = ""
        for company in blacklist.difference(set(config["blacklist"])):
            s += company + ", "
        if len(s) == 0:
            s = "No companies were added to the blacklist."
        else:
            s = "Added " + s[:-2] + " to the blacklist!"

        config["blacklist"] = list(blacklist)
        save_config(config)
        COMPANIES_CHANNEL.send(s)

    def remove_from_blacklist(companies):
        config = get_config()
        blacklist = set(config["blacklist"])

        for company in companies:
            blacklist.discard(company)

        s = ""
        for company in blacklist.difference(set(config["blacklist"])):
            s += company + ", "
        if len(s) == 0:
            s = "No companies were removed from the blacklist."
        else:
            s = "Removed " + s[:-2] + " from the blacklist!"

        config["blacklist"] = list(blacklist)
        save_config(config)
        COMPANIES_CHANNEL.send(s)

    if message.author.bot:
        return

    if message.content.splitlines()[0] == "!blacklist":
        add_to_blacklist(message.content.splitlines()[1:])

    elif message.content.splitlines()[0] == "!unblacklist":
        remove_from_blacklist(message.content.splitlines()[1:])


async def get_new_roles_postings_task():
    async def send_new_roles():
        async def send_companies_list(companies):
            companies_list_string = ""
            for company in companies:
                companies_list_string += company + "\n"
            await COMPANIES_CHANNEL.send(companies_list_string)

        def get_levels_url(company):
            base = "https://www.levels.fyi/internships/?track=Software%20Engineer&timeframe=2023%20%2F%202022&search="
            return base + urllib.parse.quote_plus(company)

        def get_google_url(company):
            base = "https://www.google.com/search?q="
            return base + urllib.parse.quote_plus(company)

        config = get_config()
        posted = set(config["posted"]) # TODO: Move "posted" into a separate JSON file
        blacklist = set(config["blacklist"])

        roles = scraper.get_recent_roles()

        companies = set()
        for role in roles:
            company, title, link, picture = role

            company_and_title = company + " - " + title
            if company_and_title in posted or company in blacklist:
                continue

            companies.add(company)
            config["posted"].append(company_and_title)
            posted.add(company_and_title)

            embed = discord.Embed(title=title, url=link, color=discord.Color.from_str("#378CCF"), timestamp=datetime.datetime.now())
            embed.set_author(name=company, url=get_google_url(company))
            embed.add_field(name="Levels.fyi Link", value=f"[{company} at Levels.fyi]({get_levels_url(company)})")
            embed.set_footer(text="Made by hotsno#0001")
            embed.set_thumbnail(url=picture)
            await NEW_POSTINGS_CHANNEL.send(embed=embed)
        
        await send_companies_list(companies)
        save_config(config)

    while True:
        try:
            await TESTING_CHANNEL.send('Trying to get new roles...')
            await send_new_roles()
            await TESTING_CHANNEL.send('Succeeded. Waiting 20 minutes.')
        except Exception as e:
            await TESTING_CHANNEL.send('Failed. Waiting 20 minutes.')
            print(e)
        await asyncio.sleep(60 * 20)

def get_config():
    with open(os.path.join(sys.path[0], 'config.json')) as f:
        config = json.load(f)
        return config

def save_config(config):
    with open(os.path.join(sys.path[0], 'config.json'), 'w') as f:
        f.seek(0)
        json.dump(config, f, indent=4)
        f.truncate()


bot.run(BOT_TOKEN)
