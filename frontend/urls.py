from django.urls import path
from . import views
app_name = 'frontend'
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.signin, name='login'),
    path('register/', views.signup, name='register'),
    path('logout/', views.signout, name='logout'),
    path('documents/', views.documents, name='documents'),
    path('documents/upload/', views.upload, name='upload'),
    path('documents/<int:pk>/download/', views.download, name='download'),
    path('documents/<int:pk>/delete/', views.delete_document, name='delete'),
    path('approvals/', views.approvals, name='approvals'),
    path('approvals/<int:pk>/review/', views.approve_document, name='approve_document'),
    path('access/', views.access_requests, name='access'),
    path('access/<int:pk>/review/', views.review_access, name='review_access'),
    path('activity/', views.activity, name='activity'),
    path('reports/', views.reports, name='reports'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/password/', views.change_password, name='change_password'),
]
