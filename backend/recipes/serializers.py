from rest_framework import serializers

from api.fields import Base64ImageField
from api.mixins import IngredientValidationMixin
from api.serializers import CustomUserSerializer

from .models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    Tag,
)


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
    author = CustomUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients',
        many=True,
        read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    def _check_user_relation(self, obj, relation_name):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return getattr(obj, relation_name).filter(user=request.user).exists()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    def get_is_favorited(self, obj):
        return self._check_user_relation(obj, 'favorited')

    def get_is_in_shopping_cart(self, obj):
        return self._check_user_relation(obj, 'shopping_cart')


class RecipeWriteSerializer(
    IngredientValidationMixin,
    serializers.ModelSerializer
):
    """Сериализатор для создания и обновления рецептов."""
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

    def _save_ingredients(self, recipe, ingredients_data):
        if ingredients_data is not None:
            if hasattr(recipe, 'recipe_ingredients'):
                recipe.recipe_ingredients.all().delete()

            recipe_ingredients = [
                RecipeIngredient(
                    recipe=recipe,
                    ingredient_id=item['id'],
                    amount=item['amount']
                )
                for item in ingredients_data
            ]
            RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError('Добавьте хотя бы один тег')
        if len(set(value)) != len(value):
            raise serializers.ValidationError('Теги не должны повторяться')
        return value

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients', [])
        tags_data = validated_data.pop('tags', [])
        validated_data['author'] = self.context['request'].user

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        self._save_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)

        instance = super().update(instance, validated_data)

        if tags_data is not None:
            instance.tags.set(tags_data)

        self._save_ingredients(instance, ingredients_data)
        return instance

    def to_representation(self, instance):
        return RecipeListSerializer(instance, context=self.context).data
