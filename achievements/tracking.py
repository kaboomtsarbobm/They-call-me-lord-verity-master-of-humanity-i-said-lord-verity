from datetime import datetime, timedelta, timezone

from .models import PlayerStat


async def record_catch(discord_id, seconds=None):
    stat, _ = await PlayerStat.objects.aget_or_create(discord_id=discord_id)
    today = datetime.now(timezone.utc).date()

    stat.total_catches += 1
    stat.catch_streak += 1
    stat.best_catch_streak = max(stat.best_catch_streak, stat.catch_streak)
    stat.best_redemption = max(stat.best_redemption, stat.wrong_streak)
    stat.wrong_streak = 0

    if today.weekday() >= 5:
        stat.weekend_catches += 1

    if stat.last_catch_day == today:
        stat.catches_today += 1
    else:
        if stat.last_catch_day == today - timedelta(days=1):
            stat.daily_streak += 1
        else:
            stat.daily_streak = 1
        stat.catches_today = 1
        stat.last_catch_day = today
        stat.active_days += 1

    stat.best_daily_streak = max(stat.best_daily_streak, stat.daily_streak)
    stat.best_catches_in_day = max(stat.best_catches_in_day, stat.catches_today)

    if seconds is not None and (stat.fastest_catch is None or seconds < stat.fastest_catch):
        stat.fastest_catch = seconds
    if seconds is not None and (stat.slowest_catch is None or seconds > stat.slowest_catch):
        stat.slowest_catch = seconds

    await stat.asave()


async def record_wrong_guess(discord_id):
    stat, _ = await PlayerStat.objects.aget_or_create(discord_id=discord_id)
    stat.wrong_guesses += 1
    stat.wrong_streak += 1
    stat.best_wrong_streak = max(stat.best_wrong_streak, stat.wrong_streak)
    stat.catch_streak = 0
    await stat.asave()


async def record_late_attempt(discord_id):
    stat, _ = await PlayerStat.objects.aget_or_create(discord_id=discord_id)
    stat.late_attempts += 1
    await stat.asave()
