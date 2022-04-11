import sqlite3
import random
import string

from dotenv import load_dotenv
load_dotenv()

con = sqlite3.connect('roffleBot.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

def claimTicket(code, user):
  cur.execute('SELECT *, (SELECT COUNT(*) FROM claims WHERE claims.ticket_id = tickets.ticket_id) AS claims FROM tickets WHERE code = ?', [code])
  tickets = cur.fetchall()
  if len(tickets) == 0:
    return f"We couldn't find any tickets matching `{code}`!"
  elif len(tickets) == 1 and (tickets[0]['multi_use'] == 1 or tickets[0]['claims'] == 0):
    cur.execute('INSERT INTO claims (ticket_id, user_id, user_name, claimed) VALUES (?, ?, ?, CURRENT_TIMESTAMP)', [tickets[0]['ticket_id'], user.id, str(user)])
    con.commit()
      
    cur.execute('SELECT COUNT(*) AS count FROM claims WHERE user_id = ?', [user.id])
    userTickets = cur.fetchone()
    return f"You've succesfully claimed ticket `{ticket['code']}` from {ticket['source']}. You now have {userTickets['count']} ticket(s) in the raffle! Good luck!"
  elif len(tickets) == 1 and tickets[0]['multi_use'] == 0 and tickets[0]['claims'] > 0:
    return f"That ticket has already been claimed!"
  else:
    return f"Something went wrong trying to claim your ticket..."


import os
import discord
from discord.ext import commands
import csv
#from io import StringIO, BytesIO
#import codecs
import io
#import time

bot = commands.Bot(command_prefix="!")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TIDY = os.getenv("TIDY") == "True"

@bot.event
async def on_ready():
  print(f"Logged in as {bot.user.name}({bot.user.id})")


@bot.command()
@commands.has_role("Roffle Admin")
async def create(ctx, count, source):
  print(f"Received request to generate new tickets from {ctx.author}")
  count = int(count)
  chars = string.ascii_letters + string.digits
  codes = []
  for i in range(count):
    newCode = ''.join(random.sample(chars, 6))
    cur.execute('INSERT INTO tickets (code, source, multi_use, created) VALUES (?, ?, 0, CURRENT_TIMESTAMP)', [newCode, source])
    codes.append(newCode)
  con.commit()
  print(type(codes))
  print(type(codes[0]))
  if count <= 100:
    codesList = '\n'.join(codes)
    await ctx.author.send(f"Your {count} new raffle ticket codes for '{source}' are: ```\n{codesList}```")
  else:
    with io.BytesIO() as buffer:
      sb = io.TextIOWrapper(buffer, 'utf-8', newline='')
      csv.writer(sb).writerow(['Raffle Code','Code Source'])
      for code in codes:
        csv.writer(sb).writerow([code,source])
      sb.flush()
      buffer.seek(0)
      discoFile = discord.File(sb, filename=f'Raffle Codes - {source}.csv')
      await ctx.author.send(f"Your {count} new raffle ticket codes for '{source}' are attached.", file=discoFile)

  reply = await ctx.reply(f"I've DMed you your new raffle ticket codes.")
  if TIDY:
    await ctx.message.delete(delay=10)
    await reply.delete(delay=10)
  print(f"Replied to {ctx.author} with generated tickets")
@create.error
async def create_error(ctx, error):
  if isinstance(error, commands.MissingRole):
    reply = await ctx.reply(":warning: You must have the `Roffle Admin` role to do that!")
    if TIDY:
      await ctx.message.delete(delay=10)
      await reply.delete(delay=10)
  else:
    raise error

@bot.command()
@commands.has_role("Roffle Admin")
async def addMulti(ctx, code, source):
  print(f"Received request to add multi_use code '{code}' from {ctx.author}")
  cur.execute('INSERT INTO tickets (code, source, multi_use, created) VALUES (?, ?, 1, CURRENT_TIMESTAMP)', [code, source])
  con.commit()
  reply = await ctx.reply("Multi-use code added!")
  if TIDY:
    await ctx.message.delete(delay=10)
      await reply.delete(delay=10)


@bot.command()
async def claim(ctx, code):
  print(f"Received claim request for '{code}' from {ctx.author} ({ctx.author.id})")
  response = claimTicket(code, ctx.author)
  reply = await ctx.reply(response + ' Self destructing in 10 seconds.')
  print(f"Processed claim request for '{code}' from {ctx.author} ({ctx.author.id})")
  if TIDY:
    await ctx.message.delete(delay=10)
    await reply.delete(delay=10)

@bot.command()
@commands.is_owner()
async def ping(ctx):
  await ctx.reply("Pong!")

@bot.command()
@commands.is_owner()
async def quit(ctx):
  await ctx.reply("Exiting script, Goodbye!")
  await bot.close()
  exit()

if __name__ == "__main__":
  bot.run(DISCORD_TOKEN)