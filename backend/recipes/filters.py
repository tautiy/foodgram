from django_filters import rest_framework as filters

from .models import Recipe


class RecipeFilter(filters.FilterSet):
    """Фильтр для рецептов."""
    tags = filters.AllValuesMultipleFilter(
        field_name='tags__slug',
        lookup_expr='exact'
    )
    author = filters.NumberFilter(
        field_name='author__id',
        lookup_expr='exact'
    )
    is_favorited = filters.NumberFilter(
        method='filter_is_favorited'
    )
    is_in_shopping_cart = filters.NumberFilter(
        method='filter_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = ('tags', 'author', 'is_favorited', 'is_in_shopping_cart')

    def filter_is_favorited(self, queryset, name, value):
        """Фильтр по избранному."""
        if not self.request or not self.request.user.is_authenticated:
            return queryset.none()
        if value:
            return queryset.filter(favorited__user=self.request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """Фильтр по списку покупок."""
        if not self.request or not self.request.user.is_authenticated:
            return queryset.none()
        if value:
            return queryset.filter(shopping_cart__user=self.request.user)
        return queryset
