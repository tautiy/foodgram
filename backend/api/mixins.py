from rest_framework import permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response

from recipes.models import Favorite, ShoppingCart
from recipes.serializers import FavoriteSerializer, ShoppingCartSerializer


class IngredientValidationMixin:
    """
    Миксин для валидации ингредиентов в рецептах.
    Используется в RecipeCreateSerializer и RecipeUpdateSerializer.
    """

    def validate_ingredients(self, value):
        if value is None:
            return value

        if not value:
            raise serializers.ValidationError(
                'Добавьте хотя бы один ингредиент'
            )

        ingredient_ids = []
        for item in value:
            if 'id' not in item or 'amount' not in item:
                raise serializers.ValidationError(
                    'Каждый ингредиент должен содержать id и amount'
                )

            try:
                amount = int(item['amount'])
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    'Количество должно быть целым числом'
                )

            if amount < 1:
                raise serializers.ValidationError(
                    'Количество должно быть больше 0'
                )

            ingredient_id = item['id']
            if ingredient_id in ingredient_ids:
                raise serializers.ValidationError(
                    'Ингредиенты в рецепте не должны повторяться'
                )
            ingredient_ids.append(ingredient_id)

            item['amount'] = amount

        return value


class FavoriteCartMixin:
    """Миксин для работы с избранным и списком покупок."""

    def _handle_relation(self, request, pk, model, serializer_class,
                         verbose_name):
        """
        Универсальный метод для добавления/удаления рецепта
        в избранное или список покупок.
        """
        recipe = self.get_object()
        user = request.user

        if request.method == 'POST':
            serializer = serializer_class(
                data={'user': user.id, 'recipe': recipe.id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(user=user, recipe=recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            deleted, _ = model.objects.filter(
                user=user,
                recipe=recipe
            ).delete()
            if not deleted:
                return Response(
                    {'detail': f'Рецепта нет в {verbose_name}.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'],
            permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        return self._handle_relation(
            request, pk, Favorite, FavoriteSerializer, 'избранном'
        )

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        return self._handle_relation(
            request, pk, Favorite, FavoriteSerializer, 'избранном'
        )

    @action(detail=True, methods=['post'],
            permission_classes=[permissions.IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        return self._handle_relation(
            request, pk, ShoppingCart, ShoppingCartSerializer, 'списке покупок'
        )

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        return self._handle_relation(
            request, pk, ShoppingCart, ShoppingCartSerializer, 'списке покупок'
        )
