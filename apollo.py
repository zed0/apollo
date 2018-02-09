from discord import Message, abc
from discord.abc import GuildChannel
from discord.ext.commands import Bot, when_mentioned_or

from commands.verify import verify
from config import CONFIG
from models import User, db_session, init_tables, engine, LoggedMessage, MessageDiff

DESCRIPTION = """
Apollo is the Discord bot for the University of Warwick Computing Society, designed to augment the server with a number of utilities and website services.

To verify your account please set your Discord tag (name and 4 digit number e.g.: Foo#1337) in account settings on the UWCS website and then PM the bot your university number.
"""

bot = Bot(command_prefix=when_mentioned_or('!'), description=DESCRIPTION)


@bot.event
async def on_ready():
    if CONFIG['BOT_LOGGING']:
        # TODO: Write this to a logging file?
        print('Logged in as')
        print(str(bot.user))
        print('------')


# TODO: Welcome a user when they join and tell them to verify their account


@bot.event
async def on_message(message: Message):
    # If the message is by a bot then ignore it
    if message.author.bot:
        return

    user = db_session.query(User).filter(User.user_uid == message.author.id).first()
    if not user:
        user = User(user_uid=message.author.id,
                    username='{username}#{number}'.format(username=message.author.name,
                                                          number=message.author.discriminator))
        db_session.add(user)
    else:
        user.last_seen = message.created_at
    # Commit the session so the user is available now
    db_session.commit()

    # Only log messages that were in a public channel
    if isinstance(message.channel, GuildChannel):
        # Log the message to the database
        logged_message = LoggedMessage(message_uid=message.id, message_content=message.content, author=user.id,
                                       time_created=message.created_at, channel_name=message.channel.name)
        db_session.add(logged_message)
        db_session.commit()

    # TODO: Add karma scanning

    await bot.process_commands(message)


@bot.event
async def on_message_edit(before: Message, after: Message):
    # Only care about messages that are in public channels
    if isinstance(before.channel, GuildChannel):
        # Message wasn't pinned
        if before.pinned == after.pinned:
            # Log any edits to messages
            original_message = db_session.query(LoggedMessage).filter(LoggedMessage.message_uid == before.id).first()
            message_diff = MessageDiff(original_message=original_message.id, edit_content=after.content,
                                       time_created=after.edited_at)
            db_session.add(message_diff)
            db_session.commit()


if __name__ == '__main__':
    # Initialise the tables
    init_tables(engine)

    bot.add_command(verify)
    bot.run(CONFIG['DISCORD_TOKEN'])
