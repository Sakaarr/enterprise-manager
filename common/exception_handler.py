import traceback
from django.http import Http404
from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import ErrorDetail, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework_simplejwt.exceptions import InvalidToken


def custom_exception_handler(exc, context):
    """
    A custom exception handler that handles various types of exceptions and returns
    appropriate responses.

    Args:
        exc (Exception): The exception to be handled.
        context (dict): The context dictionary containing metadata about the request.

    Returns:
        Response: A response containing appropriate information about the exception.
    """
    drf_exception = exception_handler(exc, context)
    response = {}

    if isinstance(exc, Http404):
        # Handle Http404 exception separately
        response.update(
            {
                "error_code": 1,
                "status_code": status.HTTP_404_NOT_FOUND,
                "message": "The requested resource was not found.",
                "errors": [{"message": "Data Not Found"}],
                "data": [],
            }
        )
        return Response(response, status=status.HTTP_404_NOT_FOUND)

    if drf_exception is not None:
        if isinstance(exc, ValidationError):
            response.update(
                {
                    "error_code": 1,
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Invalid data.",
                    "errors": [drf_exception.data],
                    "data": [],
                }
            )
        elif isinstance(exc, InvalidToken):
            response.update(
                {
                    "error_code": 1,
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Invalid token.",
                    "errors": [{"message": "The provided token was invalid"}],
                    "data": [],
                }
            )
        else:
            response["error_code"] = 1
            response["status_code"] = status.HTTP_400_BAD_REQUEST
            response["message"] = exc.detail
            response["errors"] = [{str(exc.get_codes()): exc.detail}]
            response["data"] = []
        drf_exception.data = response
        return drf_exception

    if settings.DEBUG:
        traceback.print_exc()

    return Response(
        {
            "message": "Internal Server Error.",
            "error": [],
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def flatten(data):
    """
    Flatten a dictionary with nested lists or dictionaries and return a flattened dictionary
    with a specific format that combines all error messages in one level and removes the outer parent key.

    Args:
    data (dict): The dictionary to flatten.

    Returns:
    dict: The flattened dictionary.
    """
    flattened_data = {}
    for key, value in data.items():
        if isinstance(value, dict):
            # Recursively flatten any nested dictionaries.
            flattened_value = flatten(value)
            for nested_key, nested_value in flattened_value.items():
                flattened_data[nested_key] = nested_value
        elif isinstance(value, list):
            # Flatten any nested lists of dictionaries.
            for item in value:
                if isinstance(item, dict):
                    flattened_item = flatten(item)
                    for nested_key, nested_value in flattened_item.items():
                        flattened_data[nested_key] = nested_value
                elif isinstance(item, ErrorDetail):
                    # If the item is an ErrorDetail object, extract the error message.
                    flattened_data[key] = item
    return flattened_data