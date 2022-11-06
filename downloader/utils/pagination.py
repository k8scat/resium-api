from typing import Tuple


def parse_pagination_args(request, default_page=1, max_per_page=20) -> Tuple[int, int]:
    page = request.GET.get("page", default_page)
    per_page = request.GET.get("per_page", max_per_page)
    try:
        page = int(page)
        if page < default_page:
            page = default_page

        per_page = int(per_page)
        if per_page > max_per_page:
            per_page = max_per_page
        return page, per_page

    except ValueError:
        return default_page, max_per_page
