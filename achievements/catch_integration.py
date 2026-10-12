"""Catch integration for Verity Achievements.

Captures the real catch-modal interaction using a ContextVar, then checks
achievements after the original catch method succeeds. No core BallsDex files
or existing catch messages need to be modified.
"""

import logging
from contextvars import ContextVar
from functools import wraps

log = logging.getLogger("ballsdex.packages.achievements")

# The interaction is set by CountryballNamePrompt.on_submit and is available
# while that callback awaits BallSpawnView.catch_ball.
_current_catch_interaction: ContextVar[object | None] = ContextVar(
    "verity_current_catch_interaction", default=None
)


def install_catch_integration(bot) -> None:
    from ballsdex.packages.countryballs.countryball import (
        BallSpawnView,
        CountryballNamePrompt,
    )

    # Wrap the modal callback so the real Discord interaction is available to
    # the catch method, without changing countryball.py.
    original_on_submit = CountryballNamePrompt.on_submit
    if not getattr(original_on_submit, "_verity_interaction_wrapped", False):

        @wraps(original_on_submit)
        async def on_submit_with_interaction(self, interaction, *args, **kwargs):
            token = _current_catch_interaction.set(interaction)
            try:
                return await original_on_submit(self, interaction, *args, **kwargs)
            finally:
                _current_catch_interaction.reset(token)

        on_submit_with_interaction._verity_interaction_wrapped = True
        CountryballNamePrompt.on_submit = on_submit_with_interaction

    current = BallSpawnView.catch_ball
    if getattr(current, "_verity_achievements_wrapped", False):
        log.debug("Verity Achievements catch integration is already installed")
        return

    original_catch_ball = current

    @wraps(original_catch_ball)
    async def catch_ball_with_achievements(
        self, user, *, player=None, guild=None
    ):
        result = await original_catch_ball(
            self, user, player=player, guild=guild
        )

        try:
            from bd_models.models import Player
            from .achievement_service import check_achievements

            achievement_player = player
            if achievement_player is None:
                achievement_player, _ = await Player.objects.aget_or_create(
                    discord_id=user.id
                )

            interaction = _current_catch_interaction.get()
            if interaction is not None and getattr(interaction, "user", None):
                # Do not accidentally send an interaction's private notification
                # to a different player.
                if interaction.user.id != user.id:
                    interaction = None

            await check_achievements(
                achievement_player,
                interaction=interaction,
            )
        except Exception:
            # An achievement failure must never undo or break a successful catch.
            log.exception("Failed to check Verity Achievements after a catch")

        return result

    catch_ball_with_achievements._verity_achievements_wrapped = True
    BallSpawnView.catch_ball = catch_ball_with_achievements
    log.info("Verity Achievements ephemeral catch integration installed")
