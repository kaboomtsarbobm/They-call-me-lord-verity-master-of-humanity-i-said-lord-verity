"""Embed builders shared by the /achievements command and the completion message.

This module must not import Django models at module level: it is imported when the
package is loaded, before Django's app registry is ready.
"""

from pathlib import Path

import discord

DONE_COLOR = discord.Color.green()
PENDING_COLOR = discord.Color.gold()


def progress_bar(current, target, width=10):
    if target <= 0:
        return ""
    filled = width * min(current, target) // target
    return "▰" * filled + "▱" * (width - filled)


def image_file(achievement):
    """Return a discord.File for the achievement image, or None if it can't be read."""
    if not achievement.image:
        return None
    try:
        path = Path(achievement.image.path)
    except (ValueError, NotImplementedError):
        return None
    if not path.is_file():
        return None
    return discord.File(path, filename=f"achievement_{achievement.pk}{path.suffix or '.png'}")


def achievement_embed(achievement, *, currency_name, done, progress, number, total, completed):
    embed = discord.Embed(
        title=f"🏆 {achievement.title}",
        description=achievement.caption or "No description because the person who made this didnt config it",
        color=DONE_COLOR if done else PENDING_COLOR,
    )
    embed.set_author(name=f"Achievements • {completed}/{total} complete")

    embed.add_field(
        name="Status",
        value="✅ Its Done." if done else "⏳ Im waitin.",
        inline=True,
    )
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

    rewards = [text for text in (r.describe(currency_name) for r in achievement.rewards.all()) if text]
    if rewards:
        embed.add_field(name="Rewards:", value="\n".join(rewards)[:1024], inline=False)

    embed.set_footer(text=f"I WANT FREE REWARDS • Page {number}/{total}")

    file = image_file(achievement)
    if file:
        embed.set_thumbnail(url=f"attachment://{file.filename}")
    return embed, file


def completion_embed(achievement, reward_lines):
    description = f"**{achievement.title}**"
    if achievement.caption:
        description += f"\n{achievement.caption}"
    embed = discord.Embed(
        title="🎉 ACHIEVEMENT COMPLETE",
        description=description,
        color=DONE_COLOR,
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
