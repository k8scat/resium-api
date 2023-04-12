from django.utils.deprecation import MiddlewareMixin


class CorsMiddleware(MiddlewareMixin):
    """
    解决cors问题
    https://github.com/adamchainz/django-cors-headers/issues/495


    Todo: django-cors-headers 没有在请求头添加 Access-Control-Allow-Origin

    """

    def process_response(self, request, response):
        response["Access-Control-Allow-Origin"] = "*"
        return response
