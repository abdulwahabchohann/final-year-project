# Generated migration for mood analysis fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_book_sentiment_label_book_sentiment_magnitude_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='mood_scores',
            field=models.JSONField(blank=True, default=dict, help_text='Dictionary of mood scores (happy, sad, angry, relaxed, etc.)'),
        ),
        migrations.AddField(
            model_name='book',
            name='dominant_mood',
            field=models.CharField(blank=True, help_text='Primary emotional tone identified in the book', max_length=30),
        ),
        migrations.AddField(
            model_name='book',
            name='emotional_intensity',
            field=models.DecimalField(blank=True, decimal_places=3, help_text='Strength of emotional content (0.0 to 1.0)', max_digits=4, null=True),
        ),
        migrations.AddField(
            model_name='book',
            name='sentiment_confidence',
            field=models.DecimalField(blank=True, decimal_places=3, help_text='Confidence score for sentiment analysis (0.0 to 1.0)', max_digits=4, null=True),
        ),
    ]
