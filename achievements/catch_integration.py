"""Catch integration for Verity Achievements.

Checks achievement progress after a successful catch without modifying
BallsDex's original catch implementation or user-facing catch messages.
"""

import logging
from functools import wraps

log = logging.getLogger("ballsdex.packages.achievements")


def install_catch_integration(bot) -> None:
    # Import here rather than at module level.
    from ballsdex.packages.countryballs.countryball import BallSpawnView

    current = BallSpawnView.catch_ball

    # Avoid wrapping the same method more than once.
    if getattr(current, "_verity_achievements_wrapped", False):
        log.debug("Verity Achievements catch integration is already installed")
        return

    original_catch_ball = current

    @wraps(original_catch_ball)
    async def catch_ball_with_achievements(
        self,
        user,
        *,
        player=None,
        guild=None,
    ):
        # Run the original catch first, preserving its behavior and messages.
        result = await original_catch_ball(
            self,
            user,
            player=player,
            guild=guild,
        )

        try:
            from bd_models.models import Player
            from .achievement_service import check_achievements

            achievement_player = player

            if achievement_player is None:
                achievement_player, _ = await Player.objects.aget_or_create(
                    discord_id=user.id
                )

            message = getattr(self, "message", None)
            channel = getattr(message, "channel", None)

            await check_achievements(
                achievement_player,
                interaction=None,
                bot=bot,
                channel=channel,
            )

        except Exception:
            # Achievement errors must not break a successful catch.
            log.exception(
                "Failed to check Verity Achievements after a catch"
            )

        return result

    catch_ball_with_achievements._verity_achievements_wrapped = True
    BallSpawnView.catch_ball = catch_ball_with_achievements

    log.info("Verity Achievements catch integration installed")
