from pathlib import Path

import discord

DONE_COLOR = discord.Color.green()
PENDING_COLOR = discord.Color.gold()


def progress_bar(current, target, width=10):
    if target <= 0:
        return ""
    filled = width * min(current, target) // target
    return "▰" * filled + "▱" * (width - filled)


def parse_color(text, default):
    value = (text or "").strip().lstrip("#")
    if len(value) != 6:
        return default
    try:
        return discord.Color(int(value, 16))
    except ValueError:
        return default


def image_file(achievement):
    if not achievement.image:
        return None
    try:
        path = Path(achievement.image.path)
    except (ValueError, NotImplementedError):
        return None
    if not path.is_file():
        return None
    return discord.File(path, filename=f"achievement_{achievement.pk}{path.suffix or '.png'}")


def achievement_embed(achievement, *, currency_name, done, progress, number, total, completed, locked_by=None):
    color = parse_color(achievement.color, DONE_COLOR if done else PENDING_COLOR)
    footer = f"I WANT FREE REWARDS • Page {number}/{total}"
    if achievement.category:
        footer = f"{achievement.category} • {footer}"
    author = f"Achievements • {completed}/{total} complete"

    if achievement.hidden and not done:
        embed = discord.Embed(title="Hidden achievement.", description="???", color=color)
        embed.set_author(name=author)
        embed.add_field(name="Status", value="⏳ Im waitin.", inline=False)
        embed.set_footer(text=footer)
        return embed, None

    embed = discord.Embed(
        title=f"{achievement.emoji or '🏆'} {achievement.title}",
        description=achievement.caption or "No description.",
        color=color,
    )
    embed.set_author(name=author)

    if done:
        status = "✅ Its Done."
    elif locked_by:
        status = f"🔒 Complete **{locked_by}** first."
    else:
        status = "⏳ Im waitin."
    embed.add_field(name="Status", value=status, inline=True)

    if progress is not None:
        current, target = progress
        if done:
            current = target
        embed.add_field(
            name="Progress",
            value=f"{progress_bar(current, target)}\n{current}/{target}",
            inline=True,
        )

    embed.add_field(name="Goal", value=achievement.requirement_text(), inline=False)

    if achievement.max_winners:
        claimed = getattr(achievement, "claimed", 0)
        embed.add_field(name="Limited", value=f"{claimed}/{achievement.max_winners} claimed", inline=False)

    rewards = [text for text in (r.describe(currency_name) for r in achievement.rewards.all()) if text]
    if rewards:
        embed.add_field(name="Reward:", value="\n".join(rewards)[:1024], inline=False)

    embed.set_footer(text=footer)

    file = image_file(achievement)
    if file:
        embed.set_thumbnail(url=f"attachment://{file.filename}")
    return embed, file


def completion_embed(achievement, reward_lines):
    description = f"**{achievement.title}**"
    if achievement.caption:
        description += f"\n{achievement.caption}"
    if achievement.completion_message:
        description += f"\n\n{achievement.completion_message}"
    embed = discord.Embed(
        title=f"{achievement.emoji or '🎉'} ACHIEVEMENT COMPLETE",
        description=description,
        color=parse_color(achievement.color, DONE_COLOR),
    )
    embed.add_field(
        name="Rewards Given:",
        value="\n".join(reward_lines)[:1024] or "No reward configured.",
        inline=False,
    )
    file = image_file(achievement)
    if file:
        embed.set_thumbnail(url=f"attachment://{file.filename}")
    return embed, file
