from rest_framework.request import Request

from downloader.models import User


def get_user_from_session(request: Request):
    uid = request.session.get("uid")
    try:
        return User.objects.get(uid=uid)
    except User.DoesNotExist:
        return None


def update_user_point(user: User, point: int):
    user.point -= point
    user.used_point += point
    user.save()
