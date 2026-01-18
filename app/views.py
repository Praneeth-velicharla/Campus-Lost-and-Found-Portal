from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import CollegeUserCreationForm, LostItemForm, FoundItemForm
from .models import LostItem, FoundItem, MatchNotificationStatus, UserProfile
from fuzzywuzzy import fuzz
from django.db.models import Q

MATCH_THRESHOLD = 70   # ✅ Centralized threshold


# ---------- FUZZY MATCHING LOGIC ----------
def check_for_matches(item, item_type='lost'):
    """
    Matches LOST items with FOUND items.
    Only returns matches where score > 70.
    """
    if item_type != 'lost':
        return []

    lost_item = item

    potential_matches = FoundItem.objects.filter(~Q(user=lost_item.user))

    actioned_match_ids = MatchNotificationStatus.objects.filter(
        lost_item=lost_item,
        notified_user=lost_item.user
    ).values_list('found_item_id', flat=True)

    lost_text = f"{lost_item.name} {lost_item.description} {lost_item.features}".lower()

    matches = []

    for found_item in potential_matches:

        if found_item.id in actioned_match_ids:
            continue

        found_text = f"{found_item.name} {found_item.description} {found_item.features}".lower()
        score = fuzz.token_sort_ratio(lost_text, found_text)

        # ✅ MAIN FILTER
        if score < MATCH_THRESHOLD:
            continue

        found_user = found_item.user

        try:
            phone = found_user.userprofile.phone_number
        except UserProfile.DoesNotExist:
            phone = "N/A"

        matches.append({
            "lost_item_id": lost_item.id,
            "lost_item_name": lost_item.name,
            "found_item_id": found_item.id,
            "found_item_name": found_item.name,
            "found_user_name": found_user.username,
            "found_user_email": found_user.email,
            "found_user_phone": phone,
            "found_item_photo_url": found_item.photo.url if found_item.photo else "",
            "score": score,
        })

    return matches


# ---------- INDEX ----------
def index_view(request):
    lost_items = LostItem.objects.filter(user__isnull=False).order_by("-date_reported")
    found_items = FoundItem.objects.filter(user__isnull=False).order_by("-date_reported")

    return render(request, "index.html", {
        "lost_items": lost_items,
        "found_items": found_items
    })


# ---------- SIGNUP ----------
def signup_view(request):
    if request.method == "POST":
        form = CollegeUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Account created successfully!")
            return redirect("login")
        messages.error(request, "❌ Fix the errors below.")
    else:
        form = CollegeUserCreationForm()

    return render(request, "signup.html", {"form": form})


# ---------- LOGIN ----------
def login_view(request):
    if request.method == "POST":
        login_input = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user_obj = User.objects.get(email__iexact=login_input)
        except User.DoesNotExist:
            try:
                user_obj = User.objects.get(username__iexact=login_input)
            except User.DoesNotExist:
                messages.error(request, "❌ Invalid credentials.")
                return redirect("login")

        user = authenticate(
            request,
            username=user_obj.username,
            password=password
        )

        if user:
            login(request, user)
            return redirect("index")

        messages.error(request, "❌ Invalid credentials.")
        return redirect("login")

    return render(request, "login.html")


# ---------- DASHBOARD ----------
@login_required(login_url="login")
def dashboard_view(request):
    lost_items = LostItem.objects.filter(user=request.user).order_by("-date_reported")
    found_items = FoundItem.objects.filter(user=request.user).order_by("-date_reported")

    notifications = []

    for item in lost_items:
        matches = check_for_matches(item)

        for match in matches:
            notifications.append({
                "type": "LOST_MATCH",
                "my_item_name": match["lost_item_name"],
                "my_item_id": match["lost_item_id"],
                "match_item_name": match["found_item_name"],
                "match_user": match["found_user_name"],
                "score": match["score"],
                "match_id": match["found_item_id"]
            })

    return render(request, "dashboard.html", {
        "lost_items": lost_items,
        "found_items": found_items,
        "notifications": notifications,
        "notification_count": len(notifications)
    })


# ---------- REPORT LOST ----------
@login_required(login_url="login")
def report_lost_view(request):
    if request.method == "POST":
        form = LostItemForm(request.POST, request.FILES)
        if form.is_valid():
            lost_item = form.save(commit=False)
            lost_item.user = request.user
            lost_item.save()

            matches = check_for_matches(lost_item)

            if matches:
                messages.warning(
                    request,
                    f"🚨 {len(matches)} strong match(es) found!"
                )
            else:
                messages.success(request, "✅ Lost item reported successfully!")

            return redirect("dashboard")
    else:
        form = LostItemForm()

    return render(request, "reportlost.html", {"form": form})


# ---------- REPORT FOUND ----------
@login_required(login_url="login")
def report_found_view(request):
    if request.method == "POST":
        form = FoundItemForm(request.POST, request.FILES)
        if form.is_valid():
            found_item = form.save(commit=False)
            found_item.user = request.user
            found_item.save()

            messages.success(request, "✅ Found item reported successfully!")
            return redirect("dashboard")
    else:
        form = FoundItemForm()

    return render(request, "reportfound.html", {"form": form})


# ---------- VIEW NOTIFICATION ----------
@login_required(login_url="login")
def view_notification(request, lost_id, found_id):
    lost_item = get_object_or_404(LostItem, id=lost_id, user=request.user)
    found_item = get_object_or_404(FoundItem, id=found_id)

    lost_text = f"{lost_item.name} {lost_item.description} {lost_item.features}".lower()
    found_text = f"{found_item.name} {found_item.description} {found_item.features}".lower()
    score = fuzz.token_sort_ratio(lost_text, found_text)

    # ✅ Security validation
    if score < MATCH_THRESHOLD:
        messages.error(request, "❌ This match is no longer valid.")
        return redirect("dashboard")

    try:
        phone = found_item.user.userprofile.phone_number
    except UserProfile.DoesNotExist:
        phone = "N/A"

    return render(request, "notification.html", {
        "lost_item": lost_item,
        "found_item": found_item,
        "match_score": score,
        "found_user": {
            "username": found_item.user.username,
            "email": found_item.user.email,
            "phone": phone
        }
    })


# ---------- ACCEPT / IGNORE ----------
@login_required(login_url="login")
def handle_match_action(request, lost_id, found_id, action):
    lost_item = get_object_or_404(LostItem, id=lost_id, user=request.user)
    found_item = get_object_or_404(FoundItem, id=found_id)

    status_map = {
        "accept": "ACCEPTED",
        "ignore": "IGNORED"
    }

    if action not in status_map:
        messages.error(request, "Invalid action.")
        return redirect("dashboard")

    MatchNotificationStatus.objects.update_or_create(
        lost_item=lost_item,
        found_item=found_item,
        notified_user=request.user,
        defaults={"status": status_map[action]}
    )

    messages.success(request, f"Match {action.capitalize()}ed.")
    return redirect("dashboard")


# ---------- DELETE ----------
@login_required(login_url="login")
def delete_lost_item(request, item_id):
    LostItem.objects.filter(id=item_id, user=request.user).delete()
    messages.success(request, "🗑️ Lost item deleted.")
    return redirect("dashboard")


@login_required(login_url="login")
def delete_found_item(request, item_id):
    FoundItem.objects.filter(id=item_id, user=request.user).delete()
    messages.success(request, "🗑️ Found item deleted.")
    return redirect("dashboard")


# ---------- LOGOUT ----------
def logout_view(request):
    logout(request)
    messages.success(request, "👋 Logged out successfully.")
    return redirect("index")

def custom_404_view(request, exception):
    return render(request, "notfound.html", status=404)