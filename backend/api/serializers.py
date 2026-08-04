from rest_framework import serializers

from api.utils import User
from recipes.models import Favorite, Recipe, ShoppingCart


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """Мини-сериализатор для рецепта в избранном и корзине."""
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('id', 'name', 'image', 'cooking_time')


class BaseFavoriteOrCartSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ('user', 'recipe')

    def validate(self, data):
        user = data.get('user')
        recipe = data.get('recipe')
        model = self.Meta.model

        if model.objects.filter(user=user, recipe=recipe).exists():
            verbose_name = self.context.get('verbose_name', 'списке')
            raise serializers.ValidationError(
                f'Этот рецепт уже в {verbose_name}'
            )
        return data

    def to_representation(self, instance):
        return RecipeMinifiedSerializer(instance.recipe).data


class UserWithRecipesSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователей с рецептами (для подписок)."""
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count',
        read_only=True
    )
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar', 'recipes', 'recipes_count'
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit') if request else None
        recipes = obj.recipes.all()
        if limit:
            try:
                recipes = recipes[:int(limit)]
            except (ValueError, TypeError):
                recipes = recipes.none()
        return RecipeMinifiedSerializer(recipes, many=True).data


class CustomUserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar'
        )
        read_only_fields = ('is_subscribed',)

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.subscribers.filter(user=request.user).exists()


class FavoriteSerializer(BaseFavoriteOrCartSerializer):
    class Meta(BaseFavoriteOrCartSerializer.Meta):
        model = Favorite

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context['verbose_name'] = 'избранном'


class ShoppingCartSerializer(BaseFavoriteOrCartSerializer):
    class Meta(BaseFavoriteOrCartSerializer.Meta):
        model = ShoppingCart

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context['verbose_name'] = 'списке покупок'
