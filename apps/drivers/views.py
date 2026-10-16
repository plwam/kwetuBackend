from django.http import Http404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    ParseError,
    PermissionDenied,
    ValidationError,
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView, set_rollback
from rest_framework_simplejwt.authentication import JWTAuthentication
from apps.accounts.dashboards import stats_livreur
from apps.accounts.permissions import EstLivreurProfil
from apps.courses.exceptions import ConflitConcurrence, TransitionInvalide
from apps.drivers import services
from apps.drivers.exceptions import ErreurLivreur
from apps.drivers.permissions import EstLivreur
from apps.drivers.serializers import (
    SerialiseurCourseDisponible,
    SerialiseurCourseEnCours,
    SerialiseurCourseHistorique,
    SerialiseurLivraison,
)

def reponse_succes(donnees, statut_http=status.HTTP_200_OK):
    
    return Response(
        {"success": True, "data": donnees, "error": None}, status=statut_http
    )

def reponse_erreur(code, detail, statut_http):
    
    return Response(
        {
            "success": False,
            "data": None,
            "error": {"code": code, "detail": detail},
        },
        status=statut_http,
    )

def _aplatir_erreurs(detail):
    """Transforme le détail d'une ValidationError DRF en une phrase lisible"""
    if isinstance(detail, dict):
        return " ; ".join(f"{cle} : {_aplatir_erreurs(valeur)}" for cle, valeur in detail.items()
        )
    
    if isinstance(detail, (list, tuple)):
        return " ".join(_aplatir_erreurs(element) for element in detail)
    
    return str(detail)

def _traduire_exception(exception):
    if isinstance(exception, ErreurLivreur):
        return exception.code, exception.detail, exception.statut_http
    
    if isinstance(exception, TransitionInvalide):
        return "transition_invalide", str(exception), status.HTTP_400_BAD_REQUEST
    
    if isinstance(exception, ConflitConcurrence):
        detail = str(exception) or "Cette course n'est plus disponible."
        return "course_non_disponible", detail, status.HTTP_409_CONFLICT
    
    if isinstance(exception, (NotAuthenticated, AuthenticationFailed)):
        return (
              "non_authentifie",
              "Authentification requise : jeton absent, invalide ou expiré.",
              status.HTTP_401_UNAUTHORIZED,
        )
         
    if isinstance(exception, PermissionDenied):
        code = getattr(exception.detail, "code", None)
        
        if code not in ("acces_refuse", "compte_desactive", "compte_non_verifie"):
            code = "acces_refuse"
        return code, str(exception.detail), status.HTTP_403_FORBIDDEN
    
    if isinstance(exception, (ValidationError, ParseError)):
        return ("donnees_invalides",
            _aplatir_erreurs(exception.detail),
            status.HTTP_400_BAD_REQUEST,
        )
    
    if isinstance(exception, (NotFound, Http404)):
        return (
            "page_introuvable",
            "Cette page de résultats n'existe pas.",
            status.HTTP_404_NOT_FOUND,
        )
    
    if isinstance(exception, APIException):
        return "erreur_requete", str(exception.detail), exception.status_code
    
    return None

# -------------------------------------------------------------------------
class PaginationLivreur(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
class VueLivreurDeBase(APIView):
    """Socle commun de toutes les vues de l'espace livreur."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [EstLivreur]

    @property
    def livreur_connecte(self):
        """Le profil Livreur vient TOUJOURS du jeton, jamais de la requête."""
        return self.request.user.livreur

    def handle_exception(self, exception):
        traduction = _traduire_exception(exception)
        
        if traduction is None:
            return super().handle_exception(exception)
        code, detail, statut_http = traduction
        set_rollback()
        reponse = reponse_erreur(code, detail, statut_http)
        
        if statut_http == status.HTTP_401_UNAUTHORIZED:
            reponse["WWW-Authenticate"] = 'Bearer realm="api"'
        return reponse
    def donnees_paginees(self, queryset, classe_serialiseur, **supplements):
        paginateur = PaginationLivreur()
        page = paginateur.paginate_queryset(queryset, self.request, view=self)
        donnees = dict(supplements)
        donnees.update(
            {
                "count": paginateur.page.paginator.count,
                "page": paginateur.page.number,
                "page_size": paginateur.page.paginator.per_page,
                "results": classe_serialiseur(page, many=True).data,
            }
        )
        return donnees

    # -------------------------------------------------------------------------
class VueCoursesDisponibles(VueLivreurDeBase):
    """CU-16 VoirCourseDisponible — GET /courses/disponibles/"""

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        donnees = self.donnees_paginees(
            services.courses_disponibles(), SerialiseurCourseDisponible
        )
        return reponse_succes(donnees)

class VueCoursesEnCours(VueLivreurDeBase):
    """Courses acceptées ou récupérées — GET /courses/en-cours/"""

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        donnees = self.donnees_paginees(
            services.courses_en_cours_du_livreur(self.livreur_connecte),
            SerialiseurCourseEnCours,
        )
        return reponse_succes(donnees)

class VueHistoriqueJour(VueLivreurDeBase):
    """CU-21 ConsulterHistoriqueJour — GET /historique/"""

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        livreur = self.livreur_connecte
        donnees = self.donnees_paginees(
            services.historique_du_jour(livreur),
            SerialiseurCourseHistorique,
            date=services.date_du_jour(),
            resume=services.resume_du_jour(livreur),
        )
        return reponse_succes(donnees)

class VueAccepterCourse(VueLivreurDeBase):
    """CU-17 AccepterCourse — POST /courses/{id}/accepter/"""

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def post(self, request, pk):
        course = services.accepter_course(pk, self.livreur_connecte)
        return reponse_succes(SerialiseurCourseEnCours(course).data)

class VueMarquerRecupere(VueLivreurDeBase):
    """CU-18 MarquerColisRécupéré — POST /courses/{id}/recuperer/"""

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def post(self, request, pk):
        course = services.marquer_recupere(pk, self.livreur_connecte)
        return reponse_succes(SerialiseurCourseEnCours(course).data)

class VueLivrerAvecCode(VueLivreurDeBase):
    """CU-19 LivrerAvecCode — POST /courses/{id}/livrer/  {"code": "..."}"""

    @extend_schema(request=SerialiseurLivraison, responses=OpenApiTypes.OBJECT)
    def post(self, request, pk):
        serialiseur = SerialiseurLivraison(data=request.data)
        serialiseur.is_valid(raise_exception=True)
        course = services.livrer_avec_code(
            pk, self.livreur_connecte, serialiseur.validated_data["code"]
        )
        return reponse_succes(SerialiseurCourseEnCours(course).data)

class VueCocherPaye(VueLivreurDeBase):
    """CU-20 CocherPayé — POST /courses/{id}/payer/"""

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def post(self, request, pk):
        course = services.marquer_paye(pk, self.livreur_connecte)
        return reponse_succes(SerialiseurCourseEnCours(course).data)


class VueLivreurDashboard(VueLivreurDeBase):
    """Tableau de bord du livreur — GET /livreur/dashboard/.

    Vue d'ensemble de l'activité et du dossier du livreur : nombre de courses
    disponibles, en cours et livrées aujourd'hui, gains du jour, état de
    vérification et avancement des documents obligatoires. Cet endpoint reste
    accessible même si le compte n'est pas encore vérifié, pour que le livreur
    puisse suivre son dossier.
    """

    permission_classes = [EstLivreurProfil]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return reponse_succes(stats_livreur(self.livreur_connecte))