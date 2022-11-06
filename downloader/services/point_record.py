from downloader.models import PointRecord, User


def add_point_record(user: User, point: int, url: str, comment: str):
    PointRecord(
        user=user,
        used_point=point,
        url=url,
        comment=comment,
        point=user.point,
    ).save()
