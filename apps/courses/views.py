from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.exceptions import (
    AffectationInvalide,
    CourseDejaAffectee,
    LivreurNonEligible,
    TransitionInvalide,
)
from apps.courses.models import Course
from apps.courses.permissions import IsAdmin
from apps.courses.selectors import get_courses_admin, get_stats_dashboard
from apps.courses.serializers import (
    AssignerSerializer,
    CourseDetailSerializer,
    CourseSerializer,
)
from apps.courses.services import assigner_course


# ---------- Format commun (CONVENTIONS.md) ----------

def reponse_succes(data, http_status=status.HTTP_200_OK):
    return Response({"success": True, "data": data, "error": None}, status=http_status)


def reponse_erreur(code, detail, http_status):
    return Response(
        {"success": False, "data": None, "error": {"code": code, "detail": detail}},
        status=http_status,
    )


class PaginationStandard(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return reponse_succes(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )


# ---------- Vues ----------

class DashboardView(APIView):
    """Tableau de bord des courses (admin).

    Renvoie les compteurs du jour par statut (créées, acceptées, récupérées,
    livrées, annulées) destinés au dashboard administrateur.
    """

    permission_classes = [IsAdmin]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return reponse_succes(get_stats_dashboard())


class CourseAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """Consultation des courses par l'administrateur (lecture seule).

    Liste paginée et filtrable (``statut``, ``partenaire``, ``livreur``,
    ``zone``, ``date``) et détail d'une course incluant son historique.
    """

    permission_classes = [IsAdmin]
    pagination_class = PaginationStandard

    def get_queryset(self):
        qs = get_courses_admin(self.request.query_params)
        if self.action == "retrieve":
            qs = qs.prefetch_related("historique")
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CourseDetailSerializer
        return CourseSerializer

    def retrieve(self, request, *args, **kwargs):
        course = self.get_object()
        return reponse_succes(self.get_serializer(course).data)


class AssignerCourseView(APIView):
    """Affectation manuelle d'une course à un livreur (admin).

    Un administrateur affecte une course au statut ``creee`` à un livreur
    éligible (actif, disponible et vérifié). La course passe alors au statut
    ``acceptee``.
    """

    permission_classes = [IsAdmin]

    @extend_schema(request=AssignerSerializer, responses=CourseSerializer)
    def post(self, request, pk):
        serializer = AssignerSerializer(data=request.data)
        if not serializer.is_valid():
            return reponse_erreur(
                "donnees_invalides", serializer.errors, status.HTTP_400_BAD_REQUEST
            )

        try:
            course = assigner_course(
                pk, serializer.validated_data["livreur_id"], acteur=request.user
            )
        except Course.DoesNotExist:
            return reponse_erreur(
                "course_introuvable", "Course introuvable", status.HTTP_404_NOT_FOUND
            )
        except CourseDejaAffectee as exc:
            return reponse_erreur("course_deja_affectee", str(exc), status.HTTP_409_CONFLICT)
        except AffectationInvalide as exc:
            return reponse_erreur("affectation_invalide", str(exc), status.HTTP_409_CONFLICT)
        except LivreurNonEligible as exc:
            return reponse_erreur("livreur_non_eligible", str(exc), status.HTTP_400_BAD_REQUEST)
        except TransitionInvalide as exc:
            return reponse_erreur("transition_invalide", str(exc), status.HTTP_400_BAD_REQUEST)

        return reponse_succes(CourseSerializer(course).data)