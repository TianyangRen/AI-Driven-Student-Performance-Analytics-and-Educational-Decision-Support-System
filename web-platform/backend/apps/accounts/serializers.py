from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "full_name", "email", "role"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["username", "password", "full_name", "email", "role"]
        # role 只出现在响应里、绝不接受输入：否则任何人都能自助注册成 ADMIN
        # （is_admin 可见全系统数据）。ADMIN 只能经 Django admin / 超管授予。
        read_only_fields = ["role"]

    def create(self, validated_data):
        validated_data["role"] = "INSTRUCTOR"
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        user = authenticate(username=attrs["username"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError({"detail": "INVALID_CREDENTIALS"})
        if not user.is_active:
            raise serializers.ValidationError({"detail": "ACCOUNT_DISABLED"})
        attrs["user"] = user
        return attrs
