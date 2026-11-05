from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    """New accounts get a generated password; force the user to replace it on first login."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and user.must_change_password:
            allowed = {reverse("password_change"), reverse("logout")}
            if request.path not in allowed and not request.path.startswith(f"/{settings.STATIC_URL}"):
                return redirect("password_change")
        return self.get_response(request)
