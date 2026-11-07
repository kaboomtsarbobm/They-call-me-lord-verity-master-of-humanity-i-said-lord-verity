import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps

log = logging.getLogger("ballsdex.packages.achievements")

_submit_state: ContextVar = ContextVar("verity_submit_state", default=None)


def seconds_since_spawn(view):
    created = getattr(getattr(view, "message", None), "created_at", None)
    if created is None:
        return None
    return (datetime.now(timezone.utc) - created).total_seconds()


async def after_catch(view, user, player):
    from bd_models.models import Player

    from .achievement_service import check_achievements
    from .tracking import record_catch

    if player is None:
        player, _ = await Player.objects.aget_or_create(discord_id=user.id)

    await record_catch(user.id, seconds_since_spawn(view))

    state = _submit_state.get()
    interaction = state["interaction"] if state else None
    if interaction is not None and interaction.user.id != user.id:
        interaction = None

    await check_achievements(player, interaction=interaction)


async def check_after_miss(interaction):
    from bd_models.models import Player

    from .achievement_service import check_achievements

    player, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)
    await check_achievements(player, interaction=interaction)


async def after_wrong_guess(interaction):
    from .tracking import record_wrong_guess

    await record_wrong_guess(interaction.user.id)
    await check_after_miss(interaction)


async def after_late_attempt(interaction):
    from .tracking import record_late_attempt

    await record_late_attempt(interaction.user.id)
    await check_after_miss(interaction)


def wrap_on_submit(prompt_class):
    original = prompt_class.on_submit
    if getattr(original, "_verity_wrapped", False):
        return

    @wraps(original)
    async def on_submit_tracked(self, interaction, *args, **kwargs):
        state = {"interaction": interaction, "wrong": False}
        was_caught = bool(getattr(getattr(self, "view", None), "caught", False))
        token = _submit_state.set(state)
        try:
            result = await original(self, interaction, *args, **kwargs)
        finally:
            _submit_state.reset(token)

        try:
            if state["wrong"]:
                await after_wrong_guess(interaction)
            elif was_caught:
                await after_late_attempt(interaction)
        except Exception:
            log.exception("Failed to check Verity Achievements after a missed catch")
        return result

    on_submit_tracked._verity_wrapped = True
    prompt_class.on_submit = on_submit_tracked


def wrap_name_check(view_class):
    original = view_class.is_name_valid
    if getattr(original, "_verity_wrapped", False):
        return

    @wraps(original)
    def is_name_valid_tracked(self, text):
        valid = original(self, text)
        state = _submit_state.get()
        if not valid and state is not None:
            state["wrong"] = True
        return valid

    is_name_valid_tracked._verity_wrapped = True
    view_class.is_name_valid = is_name_valid_tracked


def wrap_catch_ball(view_class):
    original = view_class.catch_ball
    if getattr(original, "_verity_wrapped", False):
        return

    @wraps(original)
    async def catch_ball_tracked(self, user, *args, **kwargs):
        result = await original(self, user, *args, **kwargs)
        try:
            await after_catch(self, user, kwargs.get("player"))
        except Exception:
            log.exception("Failed to check Verity Achievements after a catch")
        return result

    catch_ball_tracked._verity_wrapped = True
    view_class.catch_ball = catch_ball_tracked


def install_catch_integration(bot) -> None:
    from ballsdex.packages.countryballs.countryball import (
        BallSpawnView,
        CountryballNamePrompt,
    )

    wrap_on_submit(CountryballNamePrompt)
    wrap_name_check(BallSpawnView)
    wrap_catch_ball(BallSpawnView)
    log.info("Verity Achievements catch integration installed")
