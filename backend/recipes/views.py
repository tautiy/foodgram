from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from .serializers import (
    FavoriteSerializer,
    IngredientSerializer,
    RecipeCreateSerializer,
    RecipeListSerializer,
    RecipeUpdateSerializer,
    ShoppingCartSerializer,
    TagSerializer,
)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для тегов (только чтение).
    GET /api/tags/ - список тегов
    GET /api/tags/{id}/ - получение тега
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для ингредиентов (только чтение).
    GET /api/ingredients/ - список ингредиентов (с поиском по name)
    GET /api/ingredients/{id}/ - получение ингредиента
    """
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    search_fields = ('name',)


class RecipeViewSet(viewsets.ModelViewSet):
    """
    ViewSet для рецептов.
    GET /api/recipes/ - список рецептов (с фильтрацией)
    GET /api/recipes/{id}/ - детальный просмотр
    POST /api/recipes/ - создание рецепта
    PATCH /api/recipes/{id}/ - обновление рецепта
    DELETE /api/recipes/{id}/ - удаление рецепта
    """
    queryset = Recipe.objects.all()
    serializer_class = RecipeListSerializer

    def get_permissions(self):
        if self.action in ('create',):
            return [permissions.IsAuthenticated()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.action == 'create':
            return RecipeCreateSerializer
        if self.action in ('update', 'partial_update'):
            return RecipeUpdateSerializer
        return RecipeListSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author != request.user:
            return Response(
                {'detail': 'Вы не являетесь автором этого рецепта.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author != request.user:
            return Response(
                {'detail': 'Вы не являетесь автором этого рецепта.'},
                status=status.HTTP_403_FORBIDDEN
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        """Добавить рецепт в избранное."""
        recipe = self.get_object()
        serializer = FavoriteSerializer(
            data={'user': request.user.id, 'recipe': recipe.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, recipe=recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        """Удалить рецепт из избранного."""
        recipe = self.get_object()
        deleted, _ = Favorite.objects.filter(
            user=request.user,
            recipe=recipe
        ).delete()
        if not deleted:
            return Response(
                {'detail': 'Рецепта нет в избранном.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        """Добавить рецепт в список покупок."""
        recipe = self.get_object()
        serializer = ShoppingCartSerializer(
            data={'user': request.user.id, 'recipe': recipe.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, recipe=recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        """Удалить рецепт из списка покупок."""
        recipe = self.get_object()
        deleted, _ = ShoppingCart.objects.filter(
            user=request.user,
            recipe=recipe
        ).delete()
        if not deleted:
            return Response(
                {'detail': 'Рецепта нет в списке покупок.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
