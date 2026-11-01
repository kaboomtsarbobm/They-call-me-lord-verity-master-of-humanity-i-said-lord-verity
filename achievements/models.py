from django.core.exceptions import ValidationError
from django.db import models


def _plural(amount, word):
    return f"{amount} {word}" if amount == 1 else f"{amount} {word}s"


class Achievement(models.Model):
    MANUAL = "manual"
    CATCH_BALLS = "catch_balls"
    SPECIFIC_BALLS = "specific_balls"
    UNIQUE_BALLS = "unique_balls"

    REQUIREMENT_TYPES = (
        (MANUAL, "Manual"),
        (CATCH_BALLS, "catch balls"),
        (SPECIFIC_BALLS, "catch balls but you specify them"),
        (UNIQUE_BALLS, "catch different balls"),
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title

    def requirement_text(self):
        """Short human readable goal. Prefetch required_balls to avoid extra queries."""
        if self.requirement_type == self.CATCH_BALLS:
            return f"Catch {_plural(self.requirement_amount, 'ball')}"
        if self.requirement_type == self.UNIQUE_BALLS:
            return f"Catch {_plural(self.requirement_amount, 'different ball')}"
        if self.requirement_type == self.SPECIFIC_BALLS:
            balls = [str(ball) for ball in self.required_balls.all()]
            if not balls:
                return "Catch specific balls (none selected)"
            amount = max(self.requirement_amount, 1)
            if amount == 1:
                return f"Catch: {', '.join(balls)}"
            if len(balls) == 1:
                return f"Catch {amount} {balls[0]}"
            return f"Catch {amount} of each: {', '.join(balls)}"
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

    def __str__(self):
        return f"{self.achievement.title} reward"

    def clean(self):
        if not self.currency_amount and not self.ball_id:
            raise ValidationError("https://tenor.com/view/zerobyte-verity-lord-verity-verity-no-horror-skunkz-gif-2299235693456751732")
        if self.ball_id and self.ball_amount < 1:
            raise ValidationError({"https://tenor.com/view/zerobyte-verity-lord-verity-verity-no-horror-skunkz-gif-2299235693456751732"})

    def save(self, *args, **kwargs):
        # The admin no longer asks for a reward type: it follows what was filled in.
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
            parts.append(f"{self.ball} x{self.ball_amount}")
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
