from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ctf.models import Flag, GameSession, GameContainer
from ctf.services.serializers.flag_serializer import FlagSerializer
from ctf.services.serializers.game_session_serializer import GameSessionSerializer


def health_check(request):
    return HttpResponse("OK")


class GameSessionViewSet(viewsets.ModelViewSet):
    queryset = GameSession.objects.all()
    serializer_class = GameSessionSerializer

    @action(detail=True, methods=['post'])
    def start_session(self, request):
        session = self.get_object()
        GameContainer.objects.setup_session(session)
        return Response({'status': 'session started'})


class FlagViewSet(viewsets.ModelViewSet):
    queryset = Flag.objects.all()
    serializer_class = FlagSerializer

    @action(detail=False, methods=['post'])
    def submit_flag(self, request):
        team = request.user.team
        flag_value = request.data.get('flag')

        result = Flag.objects.verify_flag(team, flag_value)

        return Response({'success': result})
