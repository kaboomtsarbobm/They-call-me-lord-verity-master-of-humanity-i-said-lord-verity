from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('achievements', '0010_customization_and_more_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='playerstat',
            name='last_catch_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='playerstat',
            name='smallest_gap',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='achievement',
            name='guess_text',
            field=models.CharField(blank=True, help_text='For the guess types: the name or text to type. Separate alternatives with ;', max_length=200),
        ),
        migrations.AlterField(
            model_name='achievement',
            name='requirement_type',
            field=models.CharField(choices=[('manual', 'Manual'), ('catch_balls', 'catch balls'), ('specific_balls', 'catch balls but you specify them'), ('unique_balls', 'catch different balls'), ('catch_special', 'own special balls'), ('duplicate_balls', 'own copies of the same ball'), ('dex_percent', 'complete a percent of the dex'), ('attack_bonus', 'own a ball with an attack bonus'), ('health_bonus', 'own a ball with a health bonus'), ('money', 'have currency'), ('servers', 'catch balls in different servers'), ('total_catches', 'catch balls (all time)'), ('catch_streak', 'catch balls in a row without a wrong guess'), ('fast_catch', 'catch a ball fast'), ('wrong_streak', 'get a name wrong in a row'), ('wrong_total', 'get names wrong in total'), ('special_variety', 'own balls from different specials'), ('regimes', 'own balls from different regimes'), ('economies', 'own balls from different economies'), ('combined_bonus', 'own a ball with a combined bonus'), ('bad_bonus', 'own a ball with a bad bonus'), ('slow_catch', 'catch a ball slowly'), ('redemption', 'catch a ball after wrong guesses'), ('too_slow', 'be too slow to catch'), ('traded_balls', 'own balls from other players'), ('special_catches', 'catch special balls (all time)'), ('rare_balls', 'own one of the rarest balls'), ('server_balls', 'own balls caught in the same server'), ('quick_catches', 'catch balls within 10 seconds'), ('first_try_catches', 'catch balls on the first try'), ('achievements_done', 'complete achievements'), ('same_regime', 'own balls from the same regime'), ('same_economy', 'own balls from the same economy'), ('guess_name', 'type a certain name as a guess'), ('guess_contains', 'type a guess containing certain text'), ('guess_length', 'type a very long guess'), ('guess_shout', 'type a guess in all caps'), ('average_ball', 'own a perfectly average ball'), ('same_special', 'own balls with the same special'), ('rarest_set', 'own the rarest balls'), ('common_set', 'own the most common balls'), ('long_name', 'own a ball with a long name'), ('short_name', 'own a ball with a short name'), ('alphabet', 'own balls starting with different letters'), ('double_catch', 'catch two balls back to back')], default='manual', max_length=50),
        ),
    ]
