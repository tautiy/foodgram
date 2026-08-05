from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.filters import RecipeFilter
from api.mixins import FavoriteCartMixin
from api.permissions import IsAuthorOrReadOnly
from .models import (
    Ingredient,
    Recipe,
    Tag,
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


class RecipeViewSet(FavoriteCartMixin, viewsets.ModelViewSet):
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
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsAuthorOrReadOnly()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeWriteSerializer
        return RecipeListSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

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
        short_link = request.build_absolute_uri(f'/s/{recipe.id}/')
        return Response({'short-link': short_link})


def recipe_short_link_redirect(request, pk):
    """Редирект с короткой ссылки на страницу рецепта во фронтенде."""
    get_object_or_404(Recipe, pk=pk)
    return redirect(f'/recipes/{pk}')
