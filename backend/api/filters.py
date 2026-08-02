from django_filters import rest_framework as filters
from recipes.models import Recipe


class RecipeFilter(filters.FilterSet):
    tags = filters.AllValuesMultipleFilter(
        field_name='tags__slug',
        lookup_expr='exact'
    )
    author = filters.NumberFilter(
        field_name='author__id',
        lookup_expr='exact'
    )
    is_favorited = filters.NumberFilter(
        method='filter_by_user_relation'
    )
    is_in_shopping_cart = filters.NumberFilter(
        method='filter_by_user_relation'
    )

    class Meta:
        model = Recipe
        fields = ('tags', 'author', 'is_favorited', 'is_in_shopping_cart')

    def filter_by_user_relation(self, queryset, name, value):
        request = self.request
        if not request or not request.user.is_authenticated:
            return queryset.none()

        if not value:
            return queryset

        relation_map = {
            'is_favorited': 'favorited__user',
            'is_in_shopping_cart': 'shopping_cart__user',
        }
        filter_kwargs = {relation_map.get(name): request.user}
        return queryset.filter(**filter_kwargs)
