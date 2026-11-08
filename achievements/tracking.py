from datetime import datetime, timezone

from .models import PlayerStat

QUICK_SECONDS = 10


async def record_catch(discord_id, seconds=None, special=False):
    stat, _ = await PlayerStat.objects.aget_or_create(discord_id=discord_id)

    stat.total_catches += 1
    stat.catch_streak += 1
    stat.best_catch_streak = max(stat.best_catch_streak, stat.catch_streak)
    stat.best_redemption = max(stat.best_redemption, stat.wrong_streak)
    if stat.wrong_streak == 0:
        stat.first_try_catches += 1
    stat.wrong_streak = 0

    if special:
        stat.special_catches += 1

    now = datetime.now(timezone.utc)
    if stat.last_catch_at is not None:
        gap = (now - stat.last_catch_at).total_seconds()
        if stat.smallest_gap is None or gap < stat.smallest_gap:
            stat.smallest_gap = gap
    stat.last_catch_at = now

    if seconds is not None:
        if seconds <= QUICK_SECONDS:
            stat.quick_catches += 1
        if stat.fastest_catch is None or seconds < stat.fastest_catch:
            stat.fastest_catch = seconds
        if stat.slowest_catch is None or seconds > stat.slowest_catch:
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
