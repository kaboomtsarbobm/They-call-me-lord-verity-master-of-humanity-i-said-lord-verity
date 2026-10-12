"""Catch integration kept entirely inside the Verity Achievements package.

The installed RandomDex/BallsDex build does not expose ballsdex.core.events or
ballsdex.core.hooks, so achievements are checked by wrapping the existing
BallSpawnView.catch_ball method when this package loads. The original catch
implementation and its user-facing messages remain untouched.
"""

import logging
from functools import wraps

from ballsdex.packages.countryballs.countryball import BallSpawnView

log = logging.getLogger("ballsdex.packages.achievements")


def install_catch_integration(bot) -> None:
    """Check achievements after a successful catch without editing countryball.py."""
    current = BallSpawnView.catch_ball
    if getattr(current, "_verity_achievements_wrapped", False):
        return

    original_catch_ball = current

    @wraps(original_catch_ball)
    async def catch_ball_with_achievements(self, user, *, player=None, guild=None):
        # Do not change the core catch result or visible catch message.
        result = await original_catch_ball(self, user, player=player, guild=guild)

        try:
            # Import Django models only after Django has finished initializing.
            from bd_models.models import Player

            achievement_player = player
            if achievement_player is None:
                achievement_player, _ = await Player.objects.aget_or_create(
                    discord_id=user.id
                )

            from .achievement_service import check_achievements

            channel = getattr(getattr(self, "message", None), "channel", None)
            await check_achievements(
                achievement_player,
                interaction=None,
                bot=bot,
                channel=channel,
            )
        except Exception:
            # An achievement/notification error must never undo or break a catch.
            log.exception("Failed to check Verity Achievements after a catch")

        return result

    catch_ball_with_achievements._verity_achievements_wrapped = True
    BallSpawnView.catch_ball = catch_ball_with_achievements
    log.info("Verity Achievements catch integration installed")
