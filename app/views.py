from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import CollegeUserCreationForm, LostItemForm, FoundItemForm
from .models import LostItem, FoundItem, MatchNotificationStatus, UserProfile
from fuzzywuzzy import fuzz
from django.db.models import Q 

# --- Fuzzy Matching Logic (REVISED: Threshold Removed) ---
def check_for_matches(item, item_type='lost'): # REMOVED threshold argument
    """
    Checks the given LostItem against FoundItems reported by other users.
    Returns a list of PENDING matching FoundItem details for the LostItem user.
    Notification filtering (score < 80%) is now disabled per request.
    """
    if item_type != 'lost':
        # Only Lost -> Found checks are performed.
        return []

    lost_item = item
    
    # 1. Potential FoundItems by other users
    potential_matches = FoundItem.objects.filter(~Q(user=lost_item.user))
    
    # 2. Get IDs of matches already actioned (ACCEPTED or IGNORED) by this lost user
    actioned_match_ids = MatchNotificationStatus.objects.filter(
        lost_item=lost_item,
        notified_user=lost_item.user
    ).values_list('found_item_id', flat=True)
    
    # Combine text fields for comprehensive matching
    lost_item_text = f"{lost_item.name} {lost_item.description} {lost_item.features}".lower()
    
    matches = []
    for found_item in potential_matches:
        # Skip if this match has already been actioned
        if found_item.id in actioned_match_ids:
            continue

        found_item_text = f"{found_item.name} {found_item.description} {found_item.features}".lower()
        
        # Score is still calculated for display but NOT used for filtering
        score = fuzz.token_sort_ratio(lost_item_text, found_item_text)
        
        # *** NO THRESHOLD CHECK HERE ***
        
        found_user = found_item.user
        
        # Retrieve contact information via UserProfile
        try:
            phone = found_user.userprofile.phone_number
        except UserProfile.DoesNotExist:
            phone = 'N/A'
        
        matches.append({
            'lost_item_id': lost_item.id,
            'lost_item_name': lost_item.name,
            'found_item_id': found_item.id,
            'found_item_name': found_item.name,
            'found_user_name': found_user.username,
            'found_user_email': found_user.email,
            'found_user_phone': phone,
            'found_item_photo_url': found_item.photo.url if found_item.photo else '',
            'score': score, 
        })
            
    return matches

# ---------- INDEX ----------
def index_view(request):
    # Only show items whose related users still exist
    lost_items = LostItem.objects.filter(user__isnull=False).order_by('-date_reported')
    found_items = FoundItem.objects.filter(user__isnull=False).order_by('-date_reported')

    return render(request, 'index.html', {
        'lost_items': lost_items,
        'found_items': found_items
    })


# ---------- SIGNUP ----------
def signup_view(request):
    if request.method == 'POST':
        form = CollegeUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Account created successfully! Please log in.')
            return redirect('login')
        else:
            messages.error(request, '❌ Please correct the errors below.')
    else:
        form = CollegeUserCreationForm()
    return render(request, 'signup.html', {'form': form})


# ---------- LOGIN ----------
def login_view(request):
    if request.method == 'POST':
        login_input = request.POST.get('email')
        password = request.POST.get('password')
        user = None

        try:
            # 1. First, try to find the user by email (always unique)
            user_obj = User.objects.get(email__iexact=login_input)
            # Use the actual username from the found user object for authentication
            username_for_auth = user_obj.username
        except User.DoesNotExist:
            try:
                # 2. If not found by email, try to find by username
                user_obj = User.objects.get(username__iexact=login_input)
                # Use the actual username from the found user object for authentication
                username_for_auth = user_obj.username
            except User.DoesNotExist:
                # 3. User does not exist at all, or input is wrong
                messages.error(request, '❌ Invalid email or password.')
                return redirect('login')

        # Now, attempt to authenticate using the correct username and password
        user = authenticate(request, username=username_for_auth, password=password)

        if user is not None:
            login(request, user)
            # messages.success(request, f'👋 Welcome back, {user.username}!')
            return redirect('index')
        else:
            # Authentication failed (i.e., password was wrong)
            messages.error(request, '❌ Invalid email or password.')
            return redirect('login')

    return render(request, 'login.html')


# ---------- DASHBOARD ----------
@login_required(login_url='login')
def dashboard_view(request):
    lost_items = LostItem.objects.filter(user=request.user).order_by('-date_reported')
    found_items = FoundItem.objects.filter(user=request.user).order_by('-date_reported')

    # Collect notifications only for the user's LOST items (Lost -> Found only)
    notifications = []
    for item in lost_items:
        # check_for_matches call no longer requires a threshold argument
        matches = check_for_matches(item, item_type='lost') 
        
        # Structure the match data for the dashboard template
        for match in matches:
             notifications.append({
                'type': 'LOST_MATCH',
                'my_item_name': match['lost_item_name'],
                'my_item_id': match['lost_item_id'],
                'match_item_name': match['found_item_name'],
                'match_user': match['found_user_name'],
                'score': match['score'],
                'match_id': match['found_item_id']
            })
    
    return render(request, 'dashboard.html', {
        'user': request.user,
        'lost_items': lost_items,
        'found_items': found_items,
        'notifications': notifications,
        'notification_count': len(notifications)
    })


# ---------- REPORT LOST ----------
@login_required(login_url='login')
def report_lost_view(request):
    if request.method == 'POST':
        form = LostItemForm(request.POST, request.FILES)
        if form.is_valid():
            lost_item = form.save(commit=False)
            lost_item.user = request.user
            lost_item.save()
            messages.success(request, "✅ Lost item reported successfully!")
            
            # CHECK FOR IMMEDIATE MATCHES
            # check_for_matches call no longer requires a threshold argument
            matches = check_for_matches(lost_item, item_type='lost')
            if matches:
                 messages.warning(request, f"🚨 We found {len(matches)} potential match(es) for your item! Check your dashboard notifications.")
                
            return redirect('dashboard')
        else:
            messages.error(request, "❌ Please correct the errors below.")
    else:
        form = LostItemForm()
    
    # Get user's lost items count for display on the report form
    lost_items_count = LostItem.objects.filter(user=request.user).count() 
    return render(request, 'reportlost.html', {'form': form, 'lost_items': {'count': lost_items_count}}) 


# ---------- REPORT FOUND ----------
@login_required(login_url='login')
def report_found_view(request):
    if request.method == 'POST':
        form = FoundItemForm(request.POST, request.FILES)
        if form.is_valid():
            found_item = form.save(commit=False)
            found_item.user = request.user
            found_item.save()
            messages.success(request, "✅ Found item reported successfully!")
            
            # Potential matches will be calculated and the LOST item owners will be notified 
            # when they view their dashboard, according to the new logic.
            messages.info(request, "Your found item has been registered. Any potential matches will automatically notify the owner of the lost item.")

            return redirect('dashboard')
        else:
            messages.error(request, "❌ Please correct the errors below.")
    else:
        form = FoundItemForm()

    # Get user's found items count for display on the report form
    found_items_count = FoundItem.objects.filter(user=request.user).count() 
    return render(request, 'reportfound.html', {'form': form, 'found_items': {'count': found_items_count}})


# ---------- NEW: View Notification Details ----------
@login_required(login_url='login')
def view_notification(request, lost_id, found_id):
    lost_item = get_object_or_404(LostItem, id=lost_id, user=request.user)
    found_item = get_object_or_404(FoundItem, id=found_id)

    # 1. Check if this match has already been processed by the Lost User
    status_entry = MatchNotificationStatus.objects.filter(
        lost_item=lost_item,
        found_item=found_item,
        notified_user=request.user
    ).first()

    if status_entry and status_entry.status != 'PENDING':
        messages.info(request, f"This match was already marked as {status_entry.status.capitalize()}.")
        return redirect('dashboard')
        
    # 2. Calculate score for display (security check removed per request)
    lost_text = f"{lost_item.name} {lost_item.description} {lost_item.features}".lower()
    found_text = f"{found_item.name} {found_item.description} {found_item.features}".lower()
    score = fuzz.token_sort_ratio(lost_text, found_text)
    
    # *** REMOVED: if score < 80: check ***
    
    # 3. Retrieve founder's contact info
    found_user = found_item.user
    try:
        phone = found_user.userprofile.phone_number
    except UserProfile.DoesNotExist:
        phone = 'N/A'
    
    context = {
        'lost_item': lost_item,
        'found_item': found_item,
        'match_score': score,
        'found_user': {
            'username': found_user.username,
            'email': found_user.email,
            'phone': phone,
        }
    }
    return render(request, 'notification.html', context)


# ---------- NEW: Handle Ignore/Accept Action  ----------
@login_required(login_url='login')
def handle_match_action(request, lost_id, found_id, action):
    lost_item = get_object_or_404(LostItem, id=lost_id, user=request.user)
    found_item = get_object_or_404(FoundItem, id=found_id)
    
    if action not in ['accept', 'ignore']:
        messages.error(request, "Invalid action.")
        return redirect('dashboard')

    # Determine status and message
    status_map = {
        'accept': ('ACCEPTED', "🎉 Match Accepted! This notification has been archived."),
        'ignore': ('IGNORED', "Match ignored and archived. It will no longer show as a notification."),
    }
    new_status, success_message = status_map[action]
    
    # Create or update the MatchNotificationStatus entry
    MatchNotificationStatus.objects.update_or_create(
        lost_item=lost_item,
        found_item=found_item,
        notified_user=request.user,
        defaults={'status': new_status}
    )

    messages.success(request, success_message)
    return redirect('dashboard')


# ---------- DELETE LOST / FOUND ----------
@login_required(login_url='login')
def delete_lost_item(request, item_id):
    item = get_object_or_404(LostItem, id=item_id, user=request.user)
    item.delete()
    messages.success(request, "🗑️ Lost item deleted.")
    return redirect('dashboard')


@login_required(login_url='login')
def delete_found_item(request, item_id):
    item = get_object_or_404(FoundItem, id=item_id, user=request.user)
    item.delete()
    messages.success(request, "🗑️ Found item deleted.")
    return redirect('dashboard')


# ---------- LOGOUT ----------
def logout_view(request):
    logout(request)
    messages.success(request, '👋 You have been logged out successfully.')
    return redirect('index')


