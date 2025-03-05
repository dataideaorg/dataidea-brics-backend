from django.shortcuts import render
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Avg, Sum, F, Q
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta

from .models import (
    Project, Session, Event, UserPrompt, 
    AIResponse, Feedback, Tag, Dashboard, Widget
)
from .serializers import (
    ProjectSerializer, SessionSerializer, EventSerializer, 
    UserPromptSerializer, AIResponseSerializer, FeedbackSerializer,
    TagSerializer, DashboardSerializer, WidgetSerializer,
    EventCreateSerializer, UserSerializer
)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'project'):
            return obj.project.owner == request.user
        return False


class ProjectViewSet(viewsets.ModelViewSet):
    """
    API endpoint for projects
    """
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    
    def get_queryset(self):
        """
        This view should return a list of all projects
        for the currently authenticated user.
        """
        user = self.request.user
        return Project.objects.filter(Q(owner=user) | Q(members=user)).distinct()
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        project = self.get_object()
        try:
            user_id = request.data.get('user_id')
            user = User.objects.get(id=user_id)
            project.members.add(user)
            return Response({'status': 'user added'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'user not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def remove_member(self, request, pk=None):
        project = self.get_object()
        try:
            user_id = request.data.get('user_id')
            user = User.objects.get(id=user_id)
            project.members.remove(user)
            return Response({'status': 'user removed'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'user not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        Get project statistics
        """
        project = self.get_object()
        
        # Time range filter
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Get events in the time range
        events = Event.objects.filter(project=project, timestamp__gte=start_date)
        
        # Calculate statistics
        total_events = events.count()
        event_types = events.values('event_type').annotate(count=Count('id'))
        
        # User prompts stats
        prompts = UserPrompt.objects.filter(event__project=project, event__timestamp__gte=start_date)
        total_prompts = prompts.count()
        avg_prompt_tokens = prompts.aggregate(avg_tokens=Avg('tokens'))['avg_tokens'] or 0
        
        # AI responses stats
        responses = AIResponse.objects.filter(event__project=project, event__timestamp__gte=start_date)
        total_responses = responses.count()
        avg_response_tokens = responses.aggregate(avg_tokens=Avg('tokens'))['avg_tokens'] or 0
        avg_latency = responses.aggregate(avg_latency=Avg('latency'))['avg_latency'] or 0
        
        # Feedback stats
        feedback = Feedback.objects.filter(event__project=project, event__timestamp__gte=start_date)
        total_feedback = feedback.count()
        avg_rating = feedback.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
        
        # Sessions stats
        sessions = Session.objects.filter(project=project, start_time__gte=start_date)
        total_sessions = sessions.count()
        
        return Response({
            'total_events': total_events,
            'event_types': event_types,
            'total_prompts': total_prompts,
            'avg_prompt_tokens': avg_prompt_tokens,
            'total_responses': total_responses,
            'avg_response_tokens': avg_response_tokens,
            'avg_latency': avg_latency,
            'total_feedback': total_feedback,
            'avg_rating': avg_rating,
            'total_sessions': total_sessions
        })


class SessionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for sessions
    """
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user_id', 'session_key']
    ordering_fields = ['start_time', 'end_time']
    
    def get_queryset(self):
        """
        Filter sessions by project and user_id
        """
        queryset = Session.objects.all()
        
        # Filter by project
        project_id = self.request.query_params.get('project', None)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # Filter by user_id
        user_id = self.request.query_params.get('user_id', None)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Only return sessions for projects the user has access to
        user = self.request.user
        return queryset.filter(Q(project__owner=user) | Q(project__members=user)).distinct()
    
    @action(detail=True, methods=['post'])
    def end_session(self, request, pk=None):
        """
        End a session by setting the end_time
        """
        session = self.get_object()
        session.end_time = timezone.now()
        session.save()
        return Response({'status': 'session ended'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def events(self, request, pk=None):
        """
        Get all events for a session
        """
        session = self.get_object()
        events = Event.objects.filter(session=session)
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)


class EventViewSet(viewsets.ModelViewSet):
    """
    API endpoint for events
    """
    queryset = Event.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ['timestamp', 'event_type']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return EventCreateSerializer
        return EventSerializer
    
    def get_queryset(self):
        """
        Filter events by project, session, and event_type
        """
        queryset = Event.objects.all()
        
        # Filter by project
        project_id = self.request.query_params.get('project', None)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # Filter by session
        session_id = self.request.query_params.get('session', None)
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        
        # Filter by event_type
        event_type = self.request.query_params.get('event_type', None)
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        # Only return events for projects the user has access to
        user = self.request.user
        return queryset.filter(Q(project__owner=user) | Q(project__members=user)).distinct()


class UserPromptViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for user prompts (read-only)
    """
    queryset = UserPrompt.objects.all()
    serializer_class = UserPromptSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['prompt_text', 'model_name']
    ordering_fields = ['tokens']
    
    def get_queryset(self):
        """
        Filter prompts by project and model_name
        """
        queryset = UserPrompt.objects.all()
        
        # Filter by project
        project_id = self.request.query_params.get('project', None)
        if project_id:
            queryset = queryset.filter(event__project_id=project_id)
        
        # Filter by model_name
        model_name = self.request.query_params.get('model_name', None)
        if model_name:
            queryset = queryset.filter(model_name=model_name)
        
        # Only return prompts for projects the user has access to
        user = self.request.user
        return queryset.filter(
            Q(event__project__owner=user) | Q(event__project__members=user)
        ).distinct()


class AIResponseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for AI responses (read-only)
    """
    queryset = AIResponse.objects.all()
    serializer_class = AIResponseSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['response_text', 'model_name']
    ordering_fields = ['tokens', 'latency']
    
    def get_queryset(self):
        """
        Filter responses by project and model_name
        """
        queryset = AIResponse.objects.all()
        
        # Filter by project
        project_id = self.request.query_params.get('project', None)
        if project_id:
            queryset = queryset.filter(event__project_id=project_id)
        
        # Filter by model_name
        model_name = self.request.query_params.get('model_name', None)
        if model_name:
            queryset = queryset.filter(model_name=model_name)
        
        # Only return responses for projects the user has access to
        user = self.request.user
        return queryset.filter(
            Q(event__project__owner=user) | Q(event__project__members=user)
        ).distinct()


class FeedbackViewSet(viewsets.ModelViewSet):
    """
    API endpoint for feedback
    """
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['comment']
    ordering_fields = ['rating']
    
    def get_queryset(self):
        """
        Filter feedback by project and rating
        """
        queryset = Feedback.objects.all()
        
        # Filter by project
        project_id = self.request.query_params.get('project', None)
        if project_id:
            queryset = queryset.filter(event__project_id=project_id)
        
        # Filter by rating
        rating = self.request.query_params.get('rating', None)
        if rating:
            queryset = queryset.filter(rating=rating)
        
        # Only return feedback for projects the user has access to
        user = self.request.user
        return queryset.filter(
            Q(event__project__owner=user) | Q(event__project__members=user)
        ).distinct()


class TagViewSet(viewsets.ModelViewSet):
    """
    API endpoint for tags
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        """
        Filter tags by project
        """
        queryset = Tag.objects.all()
        
        # Filter by project
        project_id = self.request.query_params.get('project', None)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # Only return tags for projects the user has access to
        user = self.request.user
        return queryset.filter(
            Q(project__owner=user) | Q(project__members=user)
        ).distinct()


class DashboardViewSet(viewsets.ModelViewSet):
    """
    API endpoint for dashboards
    """
    queryset = Dashboard.objects.all()
    serializer_class = DashboardSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        """
        Filter dashboards by project
        """
        queryset = Dashboard.objects.all()
        
        # Filter by project
        project_id = self.request.query_params.get('project', None)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # Only return dashboards for projects the user has access to
        user = self.request.user
        return queryset.filter(
            Q(project__owner=user) | Q(project__members=user)
        ).distinct()


class WidgetViewSet(viewsets.ModelViewSet):
    """
    API endpoint for widgets
    """
    queryset = Widget.objects.all()
    serializer_class = WidgetSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        """
        Filter widgets by dashboard
        """
        queryset = Widget.objects.all()
        
        # Filter by dashboard
        dashboard_id = self.request.query_params.get('dashboard', None)
        if dashboard_id:
            queryset = queryset.filter(dashboard_id=dashboard_id)
        
        # Only return widgets for dashboards in projects the user has access to
        user = self.request.user
        return queryset.filter(
            Q(dashboard__project__owner=user) | Q(dashboard__project__members=user)
        ).distinct()


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for users (read-only)
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
