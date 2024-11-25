from rest_framework import serializers

from ctf.models import GameSession


class GameSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameSession
        fields = '__all__'
        exclude = 'id'