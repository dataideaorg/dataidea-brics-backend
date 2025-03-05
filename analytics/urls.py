from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'projects', views.ProjectViewSet)
router.register(r'sessions', views.SessionViewSet)
router.register(r'events', views.EventViewSet)
router.register(r'prompts', views.UserPromptViewSet)
router.register(r'responses', views.AIResponseViewSet)
router.register(r'feedback', views.FeedbackViewSet)
router.register(r'tags', views.TagViewSet)
router.register(r'dashboards', views.DashboardViewSet)
router.register(r'widgets', views.WidgetViewSet)
router.register(r'users', views.UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 