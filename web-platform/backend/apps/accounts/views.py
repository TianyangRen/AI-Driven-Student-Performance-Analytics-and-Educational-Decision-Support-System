from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated

from common.responses import ok, fail
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return fail("VALIDATION_FAILED", "注册数据校验失败", 422,
                    [{"field": k, "reason": str(v[0])} for k, v in serializer.errors.items()])
    user = serializer.save()
    token, _ = Token.objects.get_or_create(user=user)
    return ok({"user": UserSerializer(user).data, "token": token.key}, status=201)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return fail("INVALID_CREDENTIALS", "账号或密码错误", 401)
    user = serializer.validated_data["user"]
    token, _ = Token.objects.get_or_create(user=user)
    return ok({
        "user": UserSerializer(user).data,
        "token": token.key,
        "access_scope": {"course_ids": [], "section_ids": []},
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return ok({"message": "logged out"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return ok({
        "user": UserSerializer(request.user).data,
        "access_scope": {"course_ids": [], "section_ids": []},
    })
