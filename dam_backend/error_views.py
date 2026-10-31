from django.http import JsonResponse


def bad_request(request, exception):
    return JsonResponse(
        {"detail": "Invalid request."},
        status=400
    )


def permission_denied(request, exception):
    return JsonResponse(
        {"detail": "Access denied."},
        status=403
    )


def page_not_found(request, exception):
    return JsonResponse(
        {"detail": "Resource not found."},
        status=404
    )


def server_error(request):
    return JsonResponse(
        {"detail": "An internal server error occurred."},
        status=500
    )
