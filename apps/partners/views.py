from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.accounts.authentication import AuthentificationCleAPI
from apps.accounts.permissions import EstPartenaire

from .permissions import EstPartenaireOwner
from .selectors import get_courses_du_partenaire
from .serializers import (
    CourseCreateSerializer,
    CourseDetailSerializer,
    StatutSerializer,
)
from .services import annuler_course


class PartenaireCourseViewSet(viewsets.ModelViewSet):
    """
    Interface partenaire pour la gestion de ses propres courses.

    ### POST /api/v1/partenaire/courses/
    **Description courte** : Créer une demande de livraison (course).

    **Description longue** : Calcule le prix côté serveur à partir des zones de
    départ et d'arrivée, puis crée la course au statut ``creee``. Le partenaire
    est déduit de sa clé API / de son JWT, jamais du corps de la requête.

    **Auth** : Clé API (``X-API-Key``) ou JWT

    **Acteurs autorisés** : PARTENAIRE

    **Restriction** : La course est créée pour le partenaire authentifié.

    **Paramètres de requête** (body) : ``zone_depart``, ``zone_arrivee``,
    ``destinataire_nom``, ``destinataire_tel``, ``description_colis``.

    **Exemple de requête** :
    ```json
    {
      "zone_depart": 1,
      "zone_arrivee": 3,
      "destinataire_nom": "Amani K.",
      "destinataire_tel": "+243970000000",
      "description_colis": "Robe en carton"
    }
    ```

    **Exemple de réponse succès (201)** :
    ```json
    {
      "id": 42,
      "reference": "GM-1042",
      "zone_depart": 1,
      "zone_arrivee": 3,
      "destinataire_nom": "Amani K.",
      "destinataire_tel": "+243970000000",
      "description_colis": "Robe en carton",
      "prix_usd": "4.00",
      "statut": "creee",
      "paye": false,
      "date_creation": "2026-10-14T08:12:00Z",
      "historique": []
    }
    ```

    **Exemples d'erreurs** :
    - 400 : ``{"success": false, "data": null, "error": {"code": "tarif_introuvable", "detail": "Aucun tarif pour ce couple de zones."}}``
    - 401 : ``{"success": false, "data": null, "error": {"code": "not_authenticated", "detail": "Authentification requise."}}``
    - 403 : ``{"success": false, "data": null, "error": {"code": "permission_denied", "detail": "Accès réservé aux partenaires."}}``

    **Codes HTTP possibles** : 201, 400, 401, 403

    ### GET /api/v1/partenaire/courses/
    **Description courte** : Lister les courses du partenaire authentifié.

    **Auth** : Clé API ou JWT — **Acteurs autorisés** : PARTENAIRE —
    **Restriction** : seules les courses du partenaire sont renvoyées.

    **Codes HTTP possibles** : 200, 401, 403

    ### GET /api/v1/partenaire/courses/{id}/
    **Description courte** : Consulter le détail d'une course.

    **Auth** : Clé API ou JWT — **Acteurs autorisés** : PARTENAIRE —
    **Restriction** : une course d'un autre partenaire renvoie **403**.

    **Codes HTTP possibles** : 200, 401, 403, 404

    ### POST /api/v1/partenaire/courses/{id}/annuler/
    **Description courte** : Annuler une course.

    **Description longue** : Autorisé uniquement pour les statuts ``creee`` et
    ``acceptee``. Passe par ``courses.changer_statut()`` et déclenche un webhook.

    **Auth** : Clé API ou JWT — **Acteurs autorisés** : PARTENAIRE —
    **Restriction** : uniquement ses propres courses.

    **Exemple de réponse succès (200)** : détail de la course au statut ``annulee``.

    **Exemples d'erreurs** :
    - 403 : course d'un autre partenaire
    - 404 : course inexistante
    - 409 : ``{"success": false, "data": null, "error": {"code": "annulation_impossible", "detail": "Cette course ne peut plus être annulée."}}``

    **Codes HTTP possibles** : 200, 401, 403, 404, 409

    ### GET /api/v1/partenaire/courses/{id}/statut/
    **Description courte** : Suivre le statut et l'historique d'une course.

    **Auth** : Clé API ou JWT — **Acteurs autorisés** : PARTENAIRE —
    **Restriction** : uniquement ses propres courses.

    **Codes HTTP possibles** : 200, 401, 403, 404
    """

    authentication_classes = [JWTAuthentication, AuthentificationCleAPI]
    permission_classes = [EstPartenaire, EstPartenaireOwner]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        """
        Filtre la liste par partenaire ; les autres actions chargent la course
        puis laissent ``EstPartenaireOwner`` renvoyer 403 en cas de non-propriété
        (et non 404), conformément au cahier des charges.
        """
        from apps.courses.models import Course

        if self.action == "list":
            return get_courses_du_partenaire(self.request.user.partenaire)
        return Course.objects.all()

    def get_serializer_class(self):
        if self.action == "create":
            return CourseCreateSerializer
        if self.action == "statut":
            return StatutSerializer
        return CourseDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        partenaire = getattr(self.request.user, "partenaire", None)
        if partenaire is not None:
            context["partenaire"] = partenaire
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.save()
        return Response(
            CourseDetailSerializer(course).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="annuler")
    def annuler(self, request, pk=None):
        course = self.get_object()
        course = annuler_course(course)
        return Response(CourseDetailSerializer(course).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="statut")
    def statut(self, request, pk=None):
        course = self.get_object()
        return Response(StatutSerializer(course).data, status=status.HTTP_200_OK)
