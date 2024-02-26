def raise_for_status(response):
    http_error_msg = ""

    if 400 <= response.status_code < 500:
        http_error_msg = (
            f"{response.status_code} Client Error for url: {response.url}"
        )

    elif 500 <= response.status_code < 600:
        http_error_msg = (
            f"{response.status_code} Server Error for url: {response.url}"
        )

    if http_error_msg:
        raise Exception(http_error_msg)
