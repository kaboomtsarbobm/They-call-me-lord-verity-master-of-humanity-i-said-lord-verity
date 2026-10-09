from asgiref.sync import sync_to_async

from bd_models.models import BallInstance, Player

from .models import Achievement, AchievementCompletion


async def get_currency_name():
    """Return the currency name configured in BallsDex settings."""
    try:
        from django.apps import apps

        for model in apps.get_models():
            field_names = {field.name for field in model._meta.get_fields()}
            if "currency_name" not in field_names:
                continue
            settings = await sync_to_async(model.objects.first)()
            if settings:
                name = getattr(settings, "currency_name", None)
                if name:
                    return str(name)
    except (ImportError, AttributeError, RuntimeError):
        pass
    return "currency"


async def check_achievements(player, interaction):
    currency_name = await get_currency_name()
    achievements = await sync_to_async(list)(
        Achievement.objects.filter(
            enabled=True
        ).prefetch_related(
            "required_balls",
            "rewards__ball",
        )
    )

    for achievement in achievements:
        already_completed = await AchievementCompletion.objects.filter(
            achievement=achievement,
            discord_id=player.discord_id,
        ).aexists()

        if already_completed:
            continue

        complete = False

        if achievement.requirement_type == "manual":
            complete = True

        elif achievement.requirement_type == "catch_balls":
            count = await BallInstance.objects.filter(
                player=player
            ).acount()

            complete = count >= achievement.requirement_amount

        elif achievement.requirement_type == "specific_balls":
            required_balls = await sync_to_async(list)(
                achievement.required_balls.all()
            )

            complete = True

            for ball in required_balls:
                if not await BallInstance.objects.filter(
                    player=player,
                    ball=ball,
                ).aexists():
                    complete = False
                    break

        elif achievement.requirement_type == "unique_balls":
            count = await BallInstance.objects.filter(
                player=player
            ).values("ball").distinct().acount()

            complete = count >= achievement.requirement_amount

        elif achievement.requirement_type == "catch_special":
            count = await BallInstance.objects.filter(
                player=player,
                special__isnull=False,
            ).acount()

            complete = count >= achievement.requirement_amount

        if not complete:
            continue

        rewards = await sync_to_async(list)(
            achievement.rewards.select_related("ball").all()
        )

        reward_text = []

        for reward in rewards:
            if reward.reward_type in ("currency", "both"):
                if reward.currency_amount:
                    await player.add_money(reward.currency_amount)

                    reward_text.append(
                        f"{reward.currency_amount} {currency_name}"
                    )

            if reward.reward_type in ("ball", "both"):
                if reward.ball:
                    for _ in range(reward.ball_amount):
                        await BallInstance.objects.acreate(
                            ball=reward.ball,
                            player=player,
                            attack_bonus=0,
                            health_bonus=0,
                        )

                    reward_text.append(
                        f"{reward.ball} x{reward.ball_amount}"
                    )

        await AchievementCompletion.objects.acreate(
            achievement=achievement,
            discord_id=player.discord_id,
        )

        reward_message = "\n".join(reward_text)

        if interaction:
            await interaction.followup.send(
                f"**FREE SURVEY COMPLETE**\n\n"
                f"**{achievement.title}**\n\n"
                f"**Random Shit Given:**\n"
                f"{reward_message or 'No reward configured.'}",
                ephemeral=True,
            )