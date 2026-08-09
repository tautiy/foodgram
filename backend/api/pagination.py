
from rest_framework.pagination import PageNumberPagination


class LimitPageNumberPagination(PageNumberPagination):
    """Пагинация с поддержкой параметра ?limit= (как ожидает фронтенд)."""
    page_size_query_param = 'limit'
