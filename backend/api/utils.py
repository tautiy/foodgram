from django.contrib.auth import get_user_model
from django.db.models import Sum
from recipes.models import RecipeIngredient


User = get_user_model()


def get_shopping_cart_ingredients(recipe_ids):
    """Возвращает сумму ингредиентов для списка рецептов."""
    return RecipeIngredient.objects.filter(
        recipe__in=recipe_ids
    ).values(
        'ingredient__name',
        'ingredient__measurement_unit'
    ).annotate(total_amount=Sum('amount'))
