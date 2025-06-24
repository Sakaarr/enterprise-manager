from rest_framework.response import Response


def error_response(status_code, message, description, data=None):
    return Response(
        {
            "error_code": 1,
            "status_code": status_code,
            "message": message,
            "errors": {"message": description},
            "data": data,
        }
    )


def success_response(status_code, message, description, data=None):
    return Response(
        {
            "error_code": 0,
            "status_code": status_code,
            "message": message,
            "description": description,
            "data": data,
        }
    )