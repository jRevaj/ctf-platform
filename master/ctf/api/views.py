from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ctf.managers.container_manager import GameContainerManager
from ctf.models import Flag, GameSession
from ctf.managers.flag_manager import FlagManager
from ctf.services.serializers.flag_serializer import FlagSerializer
from ctf.services.serializers.game_session_serializer import GameSessionSerializer


class GameSessionViewSet(viewsets.ModelViewSet):
    queryset = GameSession.objects.all()
    serializer_class = GameSessionSerializer

    @action(detail=True, methods=['post'])
    def start_session(self, request, pk=None):
        session = self.get_object()
        container_manager = GameContainerManager()
        container_manager.setup_session(session)
        return Response({'status': 'session started'})


class FlagViewSet(viewsets.ModelViewSet):
    queryset = Flag.objects.all()
    serializer_class = FlagSerializer

    @action(detail=False, methods=['post'])
    def submit_flag(self, request):
        team = request.user.team
        flag_value = request.data.get('flag')

        flag_manager = FlagManager()
        result = flag_manager.verify_flag(team, flag_value)

        return Response({'success': result})
