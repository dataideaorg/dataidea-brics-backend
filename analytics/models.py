from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import json


class Project(models.Model):
    """Project model to organize analytics data"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_projects')
    members = models.ManyToManyField(User, related_name='member_projects', blank=True)
    
    def __str__(self):
        return self.name


class Session(models.Model):
    """User session for tracking interactions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sessions')
    user_id = models.CharField(max_length=255, blank=True, null=True)  # External user ID
    session_key = models.CharField(max_length=255, unique=True)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"Session {self.session_key} - {self.start_time}"
    
    def duration(self):
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


class Event(models.Model):
    """Base event model for tracking all user and AI interactions"""
    EVENT_TYPES = (
        ('user_prompt', 'User Prompt'),
        ('ai_response', 'AI Response'),
        ('user_feedback', 'User Feedback'),
        ('user_action', 'User Action'),
        ('error', 'Error'),
        ('other', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='events')
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='events', null=True, blank=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    timestamp = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.event_type} at {self.timestamp}"


class UserPrompt(models.Model):
    """Model to store user prompts/queries to AI models"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='user_prompt')
    prompt_text = models.TextField()
    model_name = models.CharField(max_length=100, blank=True)
    tokens = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Prompt: {self.prompt_text[:50]}..."


class AIResponse(models.Model):
    """Model to store AI model responses"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='ai_response')
    prompt = models.ForeignKey(UserPrompt, on_delete=models.CASCADE, related_name='responses', null=True, blank=True)
    response_text = models.TextField()
    model_name = models.CharField(max_length=100)
    tokens = models.IntegerField(default=0)
    latency = models.FloatField(default=0.0)  # Response time in seconds
    
    def __str__(self):
        return f"Response: {self.response_text[:50]}..."


class Feedback(models.Model):
    """Model to store user feedback on AI responses"""
    RATING_CHOICES = (
        (1, '1 - Very Poor'),
        (2, '2 - Poor'),
        (3, '3 - Average'),
        (4, '4 - Good'),
        (5, '5 - Excellent'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='feedback')
    response = models.ForeignKey(AIResponse, on_delete=models.CASCADE, related_name='feedback_items')
    rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    comment = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    
    def __str__(self):
        return f"Feedback on {self.response} - Rating: {self.rating}"


class Tag(models.Model):
    """Tags for categorizing and filtering analytics data"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default="#3498db")  # Hex color code
    
    class Meta:
        unique_together = ('project', 'name')
    
    def __str__(self):
        return self.name


class Dashboard(models.Model):
    """Custom dashboards for analytics visualization"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='dashboards')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    layout = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name


class Widget(models.Model):
    """Dashboard widgets for visualizing analytics data"""
    WIDGET_TYPES = (
        ('line_chart', 'Line Chart'),
        ('bar_chart', 'Bar Chart'),
        ('pie_chart', 'Pie Chart'),
        ('table', 'Table'),
        ('counter', 'Counter'),
        ('heatmap', 'Heatmap'),
        ('text', 'Text'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name='widgets')
    title = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPES)
    query = models.JSONField(default=dict)
    position = models.JSONField(default=dict)  # {x, y, w, h} for grid layout
    
    def __str__(self):
        return f"{self.title} ({self.widget_type})"
