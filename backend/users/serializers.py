import base64
import uuid

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers

from .models import Subscription


User = get_user_model()


class CustomUserSerializer(serializers.ModelSerializer):
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
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name', 'password'
        )

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(
                base64.b64decode(imgstr),
                name=f'{uuid.uuid4()}.{ext}'
            )
        return super().to_internal_value(data)


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=False)

    class Meta:
        model = User
        fields = ('avatar',)

    def validate_avatar(self, value):
        if not value:
            raise serializers.ValidationError('Изображение не выбрано')
        return value


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
        from recipes.serializers import UserWithRecipesSerializer
        return UserWithRecipesSerializer(
            instance.author,
            context=self.context
        ).data
