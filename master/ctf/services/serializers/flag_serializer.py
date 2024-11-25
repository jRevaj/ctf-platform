from rest_framework import serializers

from ctf.models import Flag


class FlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flag
        fields = '__all__'