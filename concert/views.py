import logging
import os

import requests
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from concert.forms import LoginForm, SignUpForm
from concert.models import Concert, ConcertAttending


logger = logging.getLogger(__name__)
SONGS_SERVICE_URL = os.environ.get(
    "SONGS_SERVICE_URL",
    "http://songs-sn-labs-myhsagbaj.labs-prod-openshift-san-a45631dc5778dc6371c67d206ba9ae5c-0000.us-east.containers.appdomain.cloud",
)
PICTURES_SERVICE_URL = os.environ.get(
    "PICTURES_SERVICE_URL", "https://pictures.2gua5eyo4x7b.us-south.codeengine.appdomain.cloud"
)


def _get_service_data(base_url, endpoint):
    try:
        response = requests.get(f"{base_url.rstrip('/')}{endpoint}", timeout=5)
        response.raise_for_status()
        return response.json(), None
    except (requests.RequestException, ValueError) as error:
        logger.warning("Could not load %s%s: %s", base_url, endpoint, error)
        return None, "The service is temporarily unavailable."


def index(request):
    return render(request, "index.html")


def songs(request):
    payload, error = _get_service_data(SONGS_SERVICE_URL, "/song")
    song_list = payload.get("songs", []) if isinstance(payload, dict) else []
    return render(request, "songs.html", {"songs": song_list, "service_error": error})


def photos(request):
    payload, error = _get_service_data(PICTURES_SERVICE_URL, "/picture")
    photo_list = payload if isinstance(payload, list) else []
    return render(request, "photos.html", {"photos": photo_list, "service_error": error})


def signup(request):
    form = SignUpForm(request.POST or None)
    message = None
    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            message = "User already exists."
        else:
            user = User.objects.create_user(
                username=username, password=form.cleaned_data["password"]
            )
            auth_login(request, user)
            return redirect("index")
    return render(request, "signup.html", {"form": form, "message": message})


def login_view(request):
    form = LoginForm(request=request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        auth_login(request, form.get_user())
        return redirect("index")
    return render(request, "login.html", {"form": form})


def logout_view(request):
    auth_logout(request)
    return redirect("login")


def concerts(request):
    if not request.user.is_authenticated:
        return redirect("login")

    concert_rows = []
    for concert in Concert.objects.all().order_by("date", "id"):
        attendance = concert.attendee.filter(user=request.user).first()
        concert_rows.append({"concert": concert, "status": attendance.attending if attendance else "-"})
    return render(request, "concerts.html", {"concerts": concert_rows})


def concert_detail(request, id):
    if not request.user.is_authenticated:
        return redirect("login")

    concert = get_object_or_404(Concert, pk=id)
    attendance = concert.attendee.filter(user=request.user).first()
    return render(
        request,
        "concert_detail.html",
        {
            "concert_details": concert,
            "status": attendance.attending if attendance else "-",
            "attending_choices": ConcertAttending.AttendingChoices.choices,
        },
    )


def concert_attendee(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if request.method == "POST":
        concert = get_object_or_404(Concert, pk=request.POST.get("concert_id"))
        status = request.POST.get("attendee_choice")
        attendance, _ = ConcertAttending.objects.get_or_create(
            concert=concert,
            user=request.user,
            defaults={"attending": status},
        )
        if attendance.attending != status:
            attendance.attending = status
            attendance.save(update_fields=["attending"])
    return HttpResponseRedirect(reverse("concerts"))
