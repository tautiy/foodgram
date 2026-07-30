import json
from pathlib import Path

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Load ingredients from JSON file'

    def handle(self, *args, **options):
        data_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
        file_path = data_dir / 'data' / 'ingredients.json'

        if not file_path.exists():
            self.stdout.write(
                self.style.ERROR(f'File {file_path} does not exist')
            )
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        ingredients = []
        for item in data:
            ingredients.append(
                Ingredient(
                    name=item['name'],
                    measurement_unit=item['measurement_unit']
                )
            )

        Ingredient.objects.all().delete()
        Ingredient.objects.bulk_create(ingredients)

        self.stdout.write(
            self.style.SUCCESS(f'Loaded {len(ingredients)} ingredients')
        )
