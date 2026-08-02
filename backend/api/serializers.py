from django.contrib.auth import get_user_model
from rest_framework import serializers

from recipes.serializers import RecipeMinifiedSerializer


User = get_user_model()


class UserWithRecipesSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователей с рецептами (для подписок)."""
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count',
        read_only=True
    )

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar', 'recipes', 'recipes_count'
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit')
        recipes = obj.recipes.all()
        if limit:
            try:
                recipes = recipes[:int(limit)]
            except (ValueError, TypeError):
                recipes = recipes.none()
        return RecipeMinifiedSerializer(recipes, many=True).data
