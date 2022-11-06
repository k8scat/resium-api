def remove_url_query(url: str) -> str:
    if url.count("?") > 0:
        return url.split("?")[0]
    return url
