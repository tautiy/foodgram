from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.filters import RecipeFilter
from api.permissions import IsAuthorOrReadOnly
from .models import (
    Favorite,
    Ingredient,
    Recipe,
    ShoppingCart,
    Tag,
)
from api.serializers import (
    FavoriteSerializer,
    ShoppingCartSerializer,
)
from api.utils import get_shopping_cart_ingredients
from .serializers import (
    IngredientSerializer,
    RecipeListSerializer,
    RecipeWriteSerializer,
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
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    permission_classes = [IsAuthorOrReadOnly]

    def get_permissions(self):
        if self.action in ('create',):
            return [permissions.IsAuthenticated()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeWriteSerializer
        return RecipeListSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

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

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        """Скачать список покупок в формате TXT."""
        user = request.user
        recipes = user.shopping_cart.all().values_list('recipe', flat=True)

        if not recipes:
            return Response(
                {'detail': 'Список покупок пуст.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ingredients = get_shopping_cart_ingredients(recipes)

        shopping_list = []
        for item in ingredients:
            shopping_list.append(
                f"{item['ingredient__name']} - "
                f"{item['total_amount']} "
                f"{item['ingredient__measurement_unit']}"
            )

        response = HttpResponse(
            '\n'.join(shopping_list),
            content_type='text/plain'
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping_cart.txt"'
        )
        return response

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[permissions.AllowAny]
    )
    def get_link(self, request, pk=None):
        """Получить короткую ссылку на рецепт."""
        recipe = self.get_object()
        short_link = f"{request.build_absolute_uri('/')}s/{recipe.id}"
        return Response({'short-link': short_link})
