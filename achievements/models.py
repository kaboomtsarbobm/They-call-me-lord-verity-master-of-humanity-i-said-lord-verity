import re

from django.core.exceptions import ValidationError
from django.db import models


def _plural(amount, word):
    return f"{amount} {word}" if amount == 1 else f"{amount} {word}s"


class Achievement(models.Model):
    MANUAL = "manual"
    CATCH_BALLS = "catch_balls"
    SPECIFIC_BALLS = "specific_balls"
    UNIQUE_BALLS = "unique_balls"
    SPECIAL_BALLS = "catch_special"
    DUPLICATE_BALLS = "duplicate_balls"
    DEX_PERCENT = "dex_percent"
    ATTACK_BONUS = "attack_bonus"
    HEALTH_BONUS = "health_bonus"
    MONEY = "money"
    SERVERS = "servers"
    TOTAL_CATCHES = "total_catches"
    CATCH_STREAK = "catch_streak"
    FAST_CATCH = "fast_catch"
    WRONG_STREAK = "wrong_streak"
    WRONG_TOTAL = "wrong_total"
    SPECIAL_VARIETY = "special_variety"
    REGIMES = "regimes"
    ECONOMIES = "economies"
    COMBINED_BONUS = "combined_bonus"
    BAD_BONUS = "bad_bonus"
    SLOW_CATCH = "slow_catch"
    REDEMPTION = "redemption"
    TOO_SLOW = "too_slow"
    TRADED_BALLS = "traded_balls"
    SPECIAL_CATCHES = "special_catches"
    RARE_BALLS = "rare_balls"
    SERVER_BALLS = "server_balls"
    QUICK_CATCHES = "quick_catches"
    FIRST_TRY_CATCHES = "first_try_catches"
    ACHIEVEMENTS_DONE = "achievements_done"
    SAME_REGIME = "same_regime"
    SAME_ECONOMY = "same_economy"
    GUESS_NAME = "guess_name"
    GUESS_CONTAINS = "guess_contains"
    GUESS_LENGTH = "guess_length"
    GUESS_SHOUT = "guess_shout"
    AVERAGE_BALL = "average_ball"
    SAME_SPECIAL = "same_special"
    RAREST_SET = "rarest_set"
    COMMON_SET = "common_set"
    LONG_NAME = "long_name"
    SHORT_NAME = "short_name"
    ALPHABET = "alphabet"
    DOUBLE_CATCH = "double_catch"

    REQUIREMENT_TYPES = (
        (MANUAL, "Manual"),
        (CATCH_BALLS, "catch balls"),
        (SPECIFIC_BALLS, "catch balls but you specify them"),
        (UNIQUE_BALLS, "catch different balls"),
        (SPECIAL_BALLS, "own special balls"),
        (DUPLICATE_BALLS, "own copies of the same ball"),
        (DEX_PERCENT, "complete a percent of the dex"),
        (ATTACK_BONUS, "own a ball with an attack bonus"),
        (HEALTH_BONUS, "own a ball with a health bonus"),
        (MONEY, "have currency"),
        (SERVERS, "catch balls in different servers"),
        (TOTAL_CATCHES, "catch balls (all time)"),
        (CATCH_STREAK, "catch balls in a row without a wrong guess"),
        (FAST_CATCH, "catch a ball fast"),
        (WRONG_STREAK, "get a name wrong in a row"),
        (WRONG_TOTAL, "get names wrong in total"),
        (SPECIAL_VARIETY, "own balls from different specials"),
        (REGIMES, "own balls from different regimes"),
        (ECONOMIES, "own balls from different economies"),
        (COMBINED_BONUS, "own a ball with a combined bonus"),
        (BAD_BONUS, "own a ball with a bad bonus"),
        (SLOW_CATCH, "catch a ball slowly"),
        (REDEMPTION, "catch a ball after wrong guesses"),
        (TOO_SLOW, "be too slow to catch"),
        (TRADED_BALLS, "own balls from other players"),
        (SPECIAL_CATCHES, "catch special balls (all time)"),
        (RARE_BALLS, "own one of the rarest balls"),
        (SERVER_BALLS, "own balls caught in the same server"),
        (QUICK_CATCHES, "catch balls within 10 seconds"),
        (FIRST_TRY_CATCHES, "catch balls on the first try"),
        (ACHIEVEMENTS_DONE, "complete achievements"),
        (SAME_REGIME, "own balls from the same regime"),
        (SAME_ECONOMY, "own balls from the same economy"),
        (GUESS_NAME, "type a certain name as a guess"),
        (GUESS_CONTAINS, "type a guess containing certain text"),
        (GUESS_LENGTH, "type a very long guess"),
        (GUESS_SHOUT, "type a guess in all caps"),
        (AVERAGE_BALL, "own a perfectly average ball"),
        (SAME_SPECIAL, "own balls with the same special"),
        (RAREST_SET, "own the rarest balls"),
        (COMMON_SET, "own the most common balls"),
        (LONG_NAME, "own a ball with a long name"),
        (SHORT_NAME, "own a ball with a short name"),
        (ALPHABET, "own balls starting with different letters"),
        (DOUBLE_CATCH, "catch two balls back to back"),
    )

    title = models.CharField(max_length=100)
    caption = models.TextField(blank=True)
    image = models.ImageField(upload_to="achievements/", blank=True, null=True)
    enabled = models.BooleanField(default=True)

    requirement_type = models.CharField(
        max_length=50,
        choices=REQUIREMENT_TYPES,
        default=MANUAL,
    )
    requirement_amount = models.PositiveIntegerField(default=1)

    required_balls = models.ManyToManyField(
        "bd_models.Ball",
        blank=True,
        related_name="required_for_achievements",
    )
    guess_text = models.CharField(
        max_length=200,
        blank=True,
        help_text="For the guess types: the name or text to type. Separate alternatives with ;",
    )
    required_special = models.ForeignKey(
        "bd_models.Special",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="required_for_achievements",
        help_text="Only used by the special balls type: count just this special.",
    )

    emoji = models.CharField(
        max_length=32,
        blank=True,
        help_text="Shown before the title. Leave empty for the trophy.",
    )
    color = models.CharField(
        max_length=7,
        blank=True,
        help_text="Embed color as hex, like #FFAA00. Leave empty for the default.",
    )
    category = models.CharField(
        max_length=50,
        blank=True,
        help_text="Small label shown at the bottom of the embed.",
    )
    sort_order = models.IntegerField(
        default=0,
        help_text="Lower numbers show first in /achievements.",
    )
    hidden = models.BooleanField(
        default=False,
        help_text="Players only see ??? until they complete it.",
    )
    announce = models.BooleanField(
        default=True,
        help_text="Send the completion message to the player.",
    )
    completion_message = models.TextField(
        blank=True,
        help_text="Extra text shown in the completion message.",
    )
    requires = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="unlocks",
        help_text="Players must complete this achievement first.",
    )
    max_winners = models.PositiveIntegerField(
        default=0,
        help_text="Only the first players can complete it. 0 means no limit.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title

    def clean(self):
        if self.color and not re.fullmatch(r"#?[0-9a-fA-F]{6}", self.color.strip()):
            raise ValidationError({"color": "Use a hex color like #FFAA00."})
        seen = {self.pk}
        parent = self.requires
        while parent is not None:
            if parent.pk in seen:
                raise ValidationError({"requires": "That would make achievements require each other."})
            seen.add(parent.pk)
            parent = parent.requires

    def requirement_text(self):
        amount = self.requirement_amount
        kind = self.requirement_type
        if kind == self.CATCH_BALLS:
            return f"Catch {_plural(amount, 'ball')}"
        if kind == self.UNIQUE_BALLS:
            return f"Catch {_plural(amount, 'different ball')}"
        if kind == self.SPECIFIC_BALLS:
            balls = [str(ball) for ball in self.required_balls.all()]
            if not balls:
                return "Catch specific balls (none selected)"
            amount = max(amount, 1)
            if amount == 1:
                return f"Catch: {', '.join(balls)}"
            if len(balls) == 1:
                return f"Catch {amount} {balls[0]}"
            return f"Catch {amount} of each: {', '.join(balls)}"
        if kind == self.SPECIAL_BALLS:
            if self.required_special_id:
                return f"Own {_plural(amount, str(self.required_special) + ' ball')}"
            return f"Own {_plural(amount, 'special ball')}"
        if kind == self.DUPLICATE_BALLS:
            return f"Own {amount} copies of the same ball"
        if kind == self.DEX_PERCENT:
            return f"Complete {amount}% of the dex"
        if kind == self.ATTACK_BONUS:
            return f"Own a ball with at least +{amount}% attack"
        if kind == self.HEALTH_BONUS:
            return f"Own a ball with at least +{amount}% health"
        if kind == self.MONEY:
            return f"Have {amount} currency"
        if kind == self.SERVERS:
            return f"Catch balls in {_plural(amount, 'different server')}"
        if kind == self.TOTAL_CATCHES:
            return f"Catch {_plural(amount, 'ball')} in total"
        if kind == self.CATCH_STREAK:
            return f"Catch {_plural(amount, 'ball')} in a row without a wrong guess"
        if kind == self.FAST_CATCH:
            return f"Catch a ball within {_plural(amount, 'second')} of it spawning"
        if kind == self.WRONG_STREAK:
            return f"Get a name wrong {_plural(amount, 'time')} in a row"
        if kind == self.WRONG_TOTAL:
            return f"Get a name wrong {_plural(amount, 'time')} in total"
        if kind == self.SPECIAL_VARIETY:
            return f"Own balls from {_plural(amount, 'different special')}"
        if kind == self.REGIMES:
            return f"Own balls from {_plural(amount, 'different regime')}"
        if kind == self.ECONOMIES:
            return f"Own balls from {amount} different {'economy' if amount == 1 else 'economies'}"
        if kind == self.COMBINED_BONUS:
            return f"Own a ball with at least +{amount}% attack and health combined"
        if kind == self.BAD_BONUS:
            return f"Own a ball with an attack or health bonus of -{amount}% or worse"
        if kind == self.SLOW_CATCH:
            return f"Catch a ball at least {_plural(amount, 'second')} after it spawned"
        if kind == self.REDEMPTION:
            return f"Catch a ball right after getting it wrong {_plural(amount, 'time')} in a row"
        if kind == self.TOO_SLOW:
            return f"Be too slow to catch a ball {_plural(amount, 'time')}"
        if kind == self.TRADED_BALLS:
            return f"Own {_plural(amount, 'ball')} that came from other players"
        if kind == self.SPECIAL_CATCHES:
            return f"Catch {_plural(amount, 'special ball')} in total"
        if kind == self.RARE_BALLS:
            if amount <= 1:
                return "Own the rarest ball"
            return f"Own one of the {amount} rarest balls"
        if kind == self.SERVER_BALLS:
            return f"Own {_plural(amount, 'ball')} caught in the same server"
        if kind == self.QUICK_CATCHES:
            return f"Catch {_plural(amount, 'ball')} within 10 seconds of them spawning"
        if kind == self.FIRST_TRY_CATCHES:
            return f"Catch {_plural(amount, 'ball')} on the first try"
        if kind == self.ACHIEVEMENTS_DONE:
            return f"Complete {_plural(amount, 'achievement')}"
        if kind == self.SAME_REGIME:
            return f"Own {_plural(amount, 'ball')} from the same regime"
        if kind == self.SAME_ECONOMY:
            return f"Own {_plural(amount, 'ball')} from the same economy"
        if kind in (self.GUESS_NAME, self.GUESS_CONTAINS):
            wanted = [part.strip() for part in self.guess_text.split(";") if part.strip()]
            if kind == self.GUESS_NAME:
                if not wanted:
                    return "Type a certain name as a guess"
                if len(wanted) == 1:
                    return f'Type "{wanted[0]}" as a guess on a ball'
                return f"Type one of these as a guess on a ball: {', '.join(wanted)}"
            if not wanted:
                return "Type a guess containing certain text"
            if len(wanted) == 1:
                return f'Type a guess containing "{wanted[0]}"'
            return f"Type a guess containing one of: {', '.join(wanted)}"
        if kind == self.GUESS_LENGTH:
            return f"Type a guess that is at least {_plural(amount, 'character')} long"
        if kind == self.GUESS_SHOUT:
            return f"Type a guess in ALL CAPS with at least {_plural(amount, 'letter')}"
        if kind == self.AVERAGE_BALL:
            return f"Own {_plural(amount, 'perfectly average ball')} (0% attack and 0% health)"
        if kind == self.SAME_SPECIAL:
            return f"Own {_plural(amount, 'ball')} with the same special"
        if kind == self.RAREST_SET:
            return "Own the rarest ball" if amount <= 1 else f"Own the {amount} rarest balls"
        if kind == self.COMMON_SET:
            return "Own the most common ball" if amount <= 1 else f"Own the {amount} most common balls"
        if kind == self.LONG_NAME:
            return f"Own a ball with a name of at least {_plural(amount, 'character')}"
        if kind == self.SHORT_NAME:
            return f"Own a ball with a name of {_plural(amount, 'character')} or fewer"
        if kind == self.ALPHABET:
            return f"Own balls starting with {_plural(amount, 'different letter')}"
        if kind == self.DOUBLE_CATCH:
            return f"Catch two balls within {_plural(amount, 'second')} of each other"
        return "Awarded manually"


class AchievementReward(models.Model):
    CURRENCY = "currency"
    BALL = "ball"
    BOTH = "both"

    REWARD_TYPES = (
        (CURRENCY, "Money"),
        (BALL, "Ball(s)"),
        (BOTH, "Wowie Zowie!! How About Both!!"),
    )

    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name="rewards",
    )
    reward_type = models.CharField(
        max_length=20,
        choices=REWARD_TYPES,
        default=CURRENCY,
    )
    currency_amount = models.PositiveIntegerField(default=0)
    ball = models.ForeignKey(
        "bd_models.Ball",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="achievement_rewards",
    )
    ball_amount = models.PositiveIntegerField(default=1)
    special = models.ForeignKey(
        "bd_models.Special",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="achievement_rewards",
        help_text="Give the ball with this special.",
    )
    attack_bonus = models.IntegerField(default=0, help_text="Attack bonus of the ball given, in percent.")
    health_bonus = models.IntegerField(default=0, help_text="Health bonus of the ball given, in percent.")

    def __str__(self):
        return f"{self.achievement.title} reward"

    def clean(self):
        if not self.currency_amount and not self.ball_id:
            raise ValidationError("Set a currency amount, choose a ball, or both.")
        if self.ball_id and self.ball_amount < 1:
            raise ValidationError({"ball_amount": "Ball quantity must be at least 1."})

    def save(self, *args, **kwargs):
        if self.currency_amount and self.ball_id:
            self.reward_type = self.BOTH
        elif self.ball_id:
            self.reward_type = self.BALL
        else:
            self.reward_type = self.CURRENCY
        super().save(*args, **kwargs)

    def gives_currency(self):
        return self.reward_type in (self.CURRENCY, self.BOTH) and self.currency_amount > 0

    def gives_ball(self):
        return self.reward_type in (self.BALL, self.BOTH) and self.ball_id is not None and self.ball_amount > 0

    def describe(self, currency_name="currency"):
        parts = []
        if self.gives_currency():
            parts.append(f"{self.currency_amount} {currency_name}")
        if self.gives_ball():
            name = f"{self.special} {self.ball}" if self.special_id else str(self.ball)
            text = f"{name} x{self.ball_amount}"
            if self.attack_bonus or self.health_bonus:
                text += f" ({self.attack_bonus:+d}% ATK, {self.health_bonus:+d}% HP)"
            parts.append(text)
        return " + ".join(parts)


class AchievementCompletion(models.Model):
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name="completions",
    )
    discord_id = models.BigIntegerField(db_index=True)

    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("achievement", "discord_id"),
                name="unique_achievement_completion",
            ),
        )

    def __str__(self):
        return f"{self.discord_id} - {self.achievement.title}"


class PlayerStat(models.Model):
    discord_id = models.BigIntegerField(unique=True)
    total_catches = models.PositiveIntegerField(default=0)
    catch_streak = models.PositiveIntegerField(default=0)
    best_catch_streak = models.PositiveIntegerField(default=0)
    wrong_guesses = models.PositiveIntegerField(default=0)
    wrong_streak = models.PositiveIntegerField(default=0)
    best_wrong_streak = models.PositiveIntegerField(default=0)
    fastest_catch = models.FloatField(blank=True, null=True)
    slowest_catch = models.FloatField(blank=True, null=True)
    best_redemption = models.PositiveIntegerField(default=0)
    late_attempts = models.PositiveIntegerField(default=0)
    special_catches = models.PositiveIntegerField(default=0)
    quick_catches = models.PositiveIntegerField(default=0)
    first_try_catches = models.PositiveIntegerField(default=0)
    last_catch_at = models.DateTimeField(blank=True, null=True)
    smallest_gap = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"stats for {self.discord_id}"
