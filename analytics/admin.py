from django.contrib import admin
from .models import (
    Project, Session, Event, UserPrompt, 
    AIResponse, Feedback, Tag, Dashboard, Widget
)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at', 'updated_at')


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'project', 'user_id', 'start_time', 'end_time')
    search_fields = ('session_key', 'user_id')
    list_filter = ('start_time', 'end_time', 'project')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'project', 'session', 'timestamp')
    search_fields = ('event_type',)
    list_filter = ('event_type', 'timestamp', 'project')


@admin.register(UserPrompt)
class UserPromptAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_event_type', 'get_project', 'model_name', 'tokens')
    search_fields = ('prompt_text', 'model_name')
    list_filter = ('model_name',)
    
    def get_event_type(self, obj):
        return obj.event.event_type
    get_event_type.short_description = 'Event Type'
    
    def get_project(self, obj):
        return obj.event.project
    get_project.short_description = 'Project'


@admin.register(AIResponse)
class AIResponseAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_event_type', 'get_project', 'model_name', 'tokens', 'latency')
    search_fields = ('response_text', 'model_name')
    list_filter = ('model_name',)
    
    def get_event_type(self, obj):
        return obj.event.event_type
    get_event_type.short_description = 'Event Type'
    
    def get_project(self, obj):
        return obj.event.project
    get_project.short_description = 'Project'


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_event_type', 'get_project', 'rating')
    search_fields = ('comment',)
    list_filter = ('rating',)
    
    def get_event_type(self, obj):
        return obj.event.event_type
    get_event_type.short_description = 'Event Type'
    
    def get_project(self, obj):
        return obj.event.project
    get_project.short_description = 'Project'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'color')
    search_fields = ('name',)
    list_filter = ('project',)


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('project', 'created_at', 'updated_at')


@admin.register(Widget)
class WidgetAdmin(admin.ModelAdmin):
    list_display = ('title', 'dashboard', 'widget_type')
    search_fields = ('title',)
    list_filter = ('widget_type', 'dashboard')
