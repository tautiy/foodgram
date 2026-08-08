from rest_framework import serializers

from api.fields import Base64ImageField
from api.utils import User
from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)
from users.models import Subscription


class CustomUserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя."""
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


class CustomUserCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации пользователя."""
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name', 'password'
        )

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=password
        )
        user.first_name = validated_data.get('first_name', '')
        user.last_name = validated_data.get('last_name', '')
        user.save()
        return user


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для аватара пользователя."""
    avatar = Base64ImageField(required=False)

    class Meta:
        model = User
        fields = ('avatar',)


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


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """Мини-сериализатор для рецепта в избранном и корзине."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('id', 'name', 'image', 'cooking_time')


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

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    def _check_user_relation(self, obj, relation_name):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return getattr(obj, relation_name).filter(user=request.user).exists()

    def get_is_favorited(self, obj):
        return self._check_user_relation(obj, 'favorited')

    def get_is_in_shopping_cart(self, obj):
        return self._check_user_relation(obj, 'shopping_cart')


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов."""
    ingredients = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
    )
    tags = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
    )
    image = Base64ImageField(required=False)

    class Meta:
        model = Recipe
        fields = (
            'id', 'ingredients', 'tags', 'image', 'name',
            'text', 'cooking_time'
        )

    def validate_ingredients(self, value):
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

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError('Добавьте хотя бы один тег')
        if len(set(value)) != len(value):
            raise serializers.ValidationError('Теги не должны повторяться')
        return value

    def _save_ingredients(self, recipe, ingredients_data):
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

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        validated_data['author'] = self.context['request'].user

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        self._save_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')

        instance = super().update(instance, validated_data)
        instance.tags.set(tags_data)
        self._save_ingredients(instance, ingredients_data)
        return instance

    def to_representation(self, instance):
        return RecipeListSerializer(instance, context=self.context).data


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
        recipes = obj.recipes.all()
        limit = (
            request.query_params.get('recipes_limit') if request else None
        )
        if limit and limit.isdigit():
            recipes = recipes[:int(limit)]
        return RecipeMinifiedSerializer(recipes, many=True).data

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.subscribers.filter(user=request.user).exists()


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ('user', 'author')

    def validate(self, data):
        user = data.get('user')
        author = data.get('author')
        if user == author:
            raise serializers.ValidationError('Нельзя подписаться на себя.')
        if Subscription.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого пользователя.'
            )
        return data

    def to_representation(self, instance):
        return UserWithRecipesSerializer(
            instance.author,
            context=self.context
        ).data
