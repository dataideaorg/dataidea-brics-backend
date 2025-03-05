from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Project, Session, Event, UserPrompt, 
    AIResponse, Feedback, Tag, Dashboard, Widget
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color']


class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    members = UserSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    
    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'created_at', 'updated_at', 'owner', 'members', 'tags']


class SessionSerializer(serializers.ModelSerializer):
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = Session
        fields = ['id', 'project', 'user_id', 'session_key', 'start_time', 'end_time', 'metadata', 'duration']
    
    def get_duration(self, obj):
        return obj.duration()


class UserPromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPrompt
        fields = ['id', 'event', 'prompt_text', 'model_name', 'tokens']


class AIResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIResponse
        fields = ['id', 'event', 'prompt', 'response_text', 'model_name', 'tokens', 'latency']


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'event', 'response', 'rating', 'comment', 'tags']


class EventSerializer(serializers.ModelSerializer):
    user_prompt = UserPromptSerializer(read_only=True)
    ai_response = AIResponseSerializer(read_only=True)
    feedback = FeedbackSerializer(read_only=True)
    
    class Meta:
        model = Event
        fields = ['id', 'project', 'session', 'event_type', 'timestamp', 'metadata', 
                 'user_prompt', 'ai_response', 'feedback']


class WidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Widget
        fields = ['id', 'dashboard', 'title', 'widget_type', 'query', 'position']


class DashboardSerializer(serializers.ModelSerializer):
    widgets = WidgetSerializer(many=True, read_only=True)
    
    class Meta:
        model = Dashboard
        fields = ['id', 'project', 'name', 'description', 'layout', 'created_at', 'updated_at', 'widgets']


# Serializers for creating nested objects

class UserPromptCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPrompt
        fields = ['prompt_text', 'model_name', 'tokens']


class AIResponseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIResponse
        fields = ['response_text', 'model_name', 'tokens', 'latency']


class FeedbackCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['rating', 'comment', 'tags']


class EventCreateSerializer(serializers.ModelSerializer):
    user_prompt = UserPromptCreateSerializer(required=False)
    ai_response = AIResponseCreateSerializer(required=False)
    feedback = FeedbackCreateSerializer(required=False)
    
    class Meta:
        model = Event
        fields = ['project', 'session', 'event_type', 'timestamp', 'metadata', 
                 'user_prompt', 'ai_response', 'feedback']
    
    def create(self, validated_data):
        user_prompt_data = validated_data.pop('user_prompt', None)
        ai_response_data = validated_data.pop('ai_response', None)
        feedback_data = validated_data.pop('feedback', None)
        
        event = Event.objects.create(**validated_data)
        
        if user_prompt_data:
            UserPrompt.objects.create(event=event, **user_prompt_data)
        
        if ai_response_data:
            prompt = None
            if user_prompt_data:
                prompt = event.user_prompt
            AIResponse.objects.create(event=event, prompt=prompt, **ai_response_data)
        
        if feedback_data:
            response = None
            if ai_response_data:
                response = event.ai_response
            Feedback.objects.create(event=event, response=response, **feedback_data)
        
        return event 