import base64
import uuid

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers

from .models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    """Поле для приема изображений в формате Base64."""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(
                base64.b64decode(imgstr),
                name=f'{uuid.uuid4()}.{ext}'
            )
        return super().to_internal_value(data)


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов в рецепте."""
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка рецептов."""
    author = serializers.ReadOnlyField(source='author.username')
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients',
        many=True,
        read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.favorited.filter(user=request.user).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.shopping_cart.filter(user=request.user).exists()


class RecipeCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания рецепта."""
    ingredients = serializers.ListField(
        child=serializers.DictField(),
        write_only=True
    )
    tags = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'ingredients', 'tags', 'image', 'name',
            'text', 'cooking_time'
        )

    def validate_ingredients(self, value):
        """Проверяем, что ингредиенты переданы корректно."""
        if not value:
            raise serializers.ValidationError(
                'Добавьте хотя бы один ингредиент'
            )
        for item in value:
            if 'id' not in item or 'amount' not in item:
                raise serializers.ValidationError(
                    'Каждый ингредиент должен содержать id и amount'
                )
            if not isinstance(item['amount'], int) or item['amount'] < 1:
                raise serializers.ValidationError(
                    'Количество должно быть целым числом больше 0'
                )
        return value

    def validate_tags(self, value):
        """Проверяем, что теги переданы корректно."""
        if not value:
            raise serializers.ValidationError(
                'Добавьте хотя бы один тег'
            )
        if len(set(value)) != len(value):
            raise serializers.ValidationError(
                'Теги не должны повторяться'
            )
        return value

    def create(self, validated_data):
        """Создаем рецепт с ингредиентами и тегами."""
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        validated_data['author'] = self.context['request'].user

        recipe = Recipe.objects.create(**validated_data)

        recipe.tags.set(tags_data)

        for item in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient_id=item['id'],
                amount=item['amount']
            )

        return recipe

    def to_representation(self, instance):
        """При возврате ответа используем RecipeListSerializer."""
        return RecipeListSerializer(
            instance,
            context=self.context
        ).data


class RecipeUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления рецепта."""
    ingredients = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )
    tags = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    image = Base64ImageField(required=False)

    class Meta:
        model = Recipe
        fields = (
            'id', 'ingredients', 'tags', 'image', 'name',
            'text', 'cooking_time'
        )

    def validate_ingredients(self, value):
        """Проверяем, что ингредиенты переданы корректно."""
        if value is not None and not value:
            raise serializers.ValidationError(
                'Добавьте хотя бы один ингредиент'
            )
        if value:
            for item in value:
                if 'id' not in item or 'amount' not in item:
                    raise serializers.ValidationError(
                        'Каждый ингредиент должен содержать id и amount'
                    )
                if not isinstance(item['amount'], int) or item['amount'] < 1:
                    raise serializers.ValidationError(
                        'Количество должно быть целым числом больше 0'
                    )
        return value

    def validate_tags(self, value):
        """Проверяем, что теги переданы корректно."""
        if value is not None and not value:
            raise serializers.ValidationError(
                'Добавьте хотя бы один тег'
            )
        if value and len(set(value)) != len(value):
            raise serializers.ValidationError(
                'Теги не должны повторяться'
            )
        return value

    def update(self, instance, validated_data):
        """Обновляем рецепт."""
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tags_data is not None:
            instance.tags.set(tags_data)

        if ingredients_data is not None:
            instance.ingredients.clear()
            for item in ingredients_data:
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient_id=item['id'],
                    amount=item['amount']
                )

        return instance

    def to_representation(self, instance):
        """При возврате ответа используем RecipeListSerializer."""
        return RecipeListSerializer(
            instance,
            context=self.context
        ).data


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """Мини-сериализатор для рецепта в избранном и корзине."""
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('id', 'name', 'image', 'cooking_time')


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранного."""
    class Meta:
        model = Favorite
        fields = ('user', 'recipe')

    def validate(self, data):
        user = data.get('user')
        recipe = data.get('recipe')
        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                'Этот рецепт уже в избранном'
            )
        return data

    def to_representation(self, instance):
        return RecipeMinifiedSerializer(instance.recipe).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для списка покупок."""
    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')

    def validate(self, data):
        user = data.get('user')
        recipe = data.get('recipe')
        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                'Этот рецепт уже в списке покупок'
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
            except ValueError:
                pass
        return RecipeMinifiedSerializer(recipes, many=True).data
