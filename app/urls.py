from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('report-lost/', views.report_lost_view, name='report_lost'),
    path('report-found/', views.report_found_view, name='report_found'),
    path('delete-lost/<int:item_id>/', views.delete_lost_item, name='delete_lost'),
    path('delete-found/<int:item_id>/', views.delete_found_item, name='delete_found'),
    path('notification/<int:lost_id>/<int:found_id>/', views.view_notification, name='view_notification'),
    path('notification/action/<int:lost_id>/<int:found_id>/<str:action>/', views.handle_match_action, name='handle_match_action'),
    path('logout/', views.logout_view, name='logout'),
]
