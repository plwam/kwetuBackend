import secrets
import string
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.shortcuts import redirect, render
from django.urls import path
from django.utils.html import format_html

from .models import CleAPI, Livreur, Partenaire, User
from .services import creer_livreur, creer_partenaire


def generate_temp_password(length=12):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "nom", "prenom", "role", "actif", "date_creation")
    list_filter = ("role", "actif")
    search_fields = ("email", "nom", "prenom", "telephone")
    ordering = ("-date_creation",)
    readonly_fields = ("date_creation", "date_modification")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informations personnelles", {"fields": ("nom", "prenom", "telephone")}),
        (
            "Permissions",
            {
                "fields": (
                    "role",
                    "actif",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Dates", {"fields": ("date_creation", "date_modification")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "nom",
                    "prenom",
                    "telephone",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "creer-partenaire/",
                self.admin_site.admin_view(self.creer_partenaire_view),
                name="accounts_user_creer_partenaire",
            ),
            path(
                "creer-livreur/",
                self.admin_site.admin_view(self.creer_livreur_view),
                name="accounts_user_creer_livreur",
            ),
        ]
        return custom_urls + urls

    def creer_partenaire_view(self, request):
        if request.method == "POST":
            email = request.POST.get("email")
            nom = request.POST.get("nom")
            prenom = request.POST.get("prenom")
            telephone = request.POST.get("telephone")
            nom_boutique = request.POST.get("nom_boutique")
            url_webhook = request.POST.get("url_webhook", "")
            mot_de_passe = request.POST.get("mot_de_passe") or generate_temp_password()

            if User.objects.filter(email=email).exists():
                messages.error(
                    request, f"Un utilisateur avec l'email {email} existe déjà."
                )
                return redirect("admin:accounts_user_creer_partenaire")

            if Partenaire.objects.filter(
                nom_boutique=nom_boutique, actif=True
            ).exists():
                messages.error(
                    request,
                    f'Une boutique active avec le nom "{nom_boutique}" existe déjà.',
                )
                return redirect("admin:accounts_user_creer_partenaire")

            try:
                data = {
                    "email": email,
                    "nom": nom,
                    "prenom": prenom,
                    "telephone": telephone,
                    "mot_de_passe": mot_de_passe,
                    "nom_boutique": nom_boutique,
                    "url_webhook": url_webhook or None,
                }
                partenaire = creer_partenaire(data)
                cle_complete = getattr(partenaire, "_cle_api_complete", None)

                msg = format_html(
                    "<strong>✅ Partenaire créé avec succès !</strong><br>"
                    "<strong>⚠️ Copiez ces informations MAINTENANT (ne seront plus affichées) :</strong><br><br>"
                    "<code>Email : {}</code><br>"
                    "<code>Mot de passe temporaire : {}</code><br>"
                    "<code>Clé API : {}</code><br><br>"
                    "<em>Transmettez ces identifiants au partenaire par un canal sécurisé (clé USB, gestionnaire de mots de passe, etc.).</em>",
                    email,
                    mot_de_passe,
                    cle_complete,
                )
                messages.success(request, msg)
                return redirect("admin:accounts_user_changelist")

            except Exception as e:
                messages.error(request, f"Erreur lors de la création : {str(e)}")
                return redirect("admin:accounts_user_creer_partenaire")

        return render(
            request,
            "admin/accounts/user/creer_partenaire.html",
            {
                "title": "Créer un Partenaire (User + Profil + Clé API)",
                "opts": self.model._meta,
                "has_view_permission": True,
            },
        )

    def creer_livreur_view(self, request):
        if request.method == "POST":
            email = request.POST.get("email")
            nom = request.POST.get("nom")
            prenom = request.POST.get("prenom")
            telephone = request.POST.get("telephone")
            mot_de_passe = request.POST.get("mot_de_passe") or generate_temp_password()

            if User.objects.filter(email=email).exists():
                messages.error(
                    request, f"Un utilisateur avec l'email {email} existe déjà."
                )
                return redirect("admin:accounts_user_creer_livreur")

            try:
                data = {
                    "email": email,
                    "nom": nom,
                    "prenom": prenom,
                    "telephone": telephone,
                    "mot_de_passe": mot_de_passe,
                }
                creer_livreur(data)

                msg = format_html(
                    "<strong>✅ Livreur créé avec succès !</strong><br>"
                    "<strong>⚠️ Copiez ces informations MAINTENANT (ne seront plus affichées) :</strong><br><br>"
                    "<code>Email : {}</code><br>"
                    "<code>Mot de passe temporaire : {}</code><br><br>"
                    "<em>Transmettez ces identifiants au livreur par un canal sécurisé.</em>",
                    email,
                    mot_de_passe,
                )
                messages.success(request, msg)
                return redirect("admin:accounts_user_changelist")

            except Exception as e:
                messages.error(request, f"Erreur lors de la création : {str(e)}")
                return redirect("admin:accounts_user_creer_livreur")

        return render(
            request,
            "admin/accounts/user/creer_livreur.html",
            {
                "title": "Créer un Livreur (User + Profil)",
                "opts": self.model._meta,
                "has_view_permission": True,
            },
        )


@admin.register(Partenaire)
class PartenaireAdmin(admin.ModelAdmin):
    list_display = ("nom_boutique", "user", "actif", "date_creation", "cle_api_link")
    list_filter = ("actif",)
    search_fields = ("nom_boutique", "user__email", "user__nom")
    readonly_fields = ("date_creation", "date_modification", "cle_api_display")
    fields = (
        "user",
        "nom_boutique",
        "url_webhook",
        "actif",
        "cle_api_display",
        "date_creation",
        "date_modification",
    )
    actions = ("regenerer_cle_api",)

    @admin.action(description="Régénérer la clé API (affichée une seule fois)")
    def regenerer_cle_api(self, request, queryset):
        if queryset.count() != 1:
            messages.error(request, "Sélectionnez exactement un partenaire.")
            return

        partenaire = queryset.first()
        try:
            from .services import generer_cle_api

            cle_api, cle_complete = generer_cle_api(partenaire)

            msg = format_html(
                "<strong>✅ Clé API régénérée avec succès !</strong><br>"
                "<strong>⚠️ Copiez cette clé MAINTENANT (ne sera plus affichée) :</strong><br><br>"
                "<code>Clé API : {}</code><br><br>"
                "<em>Transmettez cette clé au partenaire par un canal sécurisé.</em>",
                cle_complete,
            )
            messages.success(request, msg)

        except Exception as e:
            messages.error(request, f"Erreur lors de la régénération : {str(e)}")

    def cle_api_display(self, obj):
        cle = obj.cle_api_active()
        if cle:
            return format_html(
                "<code>{}</code> (active depuis {})",
                cle.prefixe + "...",
                cle.date_creation.strftime("%d/%m/%Y"),
            )
        return "Aucune clé active"

    cle_api_display.short_description = "Clé API active"

    def cle_api_link(self, obj):
        cle = obj.cle_api_active()
        if cle:
            return format_html('<span class="badge badge-success">Active</span>')
        return format_html('<span class="badge badge-danger">Aucune</span>')

    cle_api_link.short_description = "Clé API"


@admin.register(Livreur)
class LivreurAdmin(admin.ModelAdmin):
    list_display = ("user", "disponible", "actif", "date_creation")
    list_filter = ("disponible", "actif")
    search_fields = ("user__email", "user__nom", "user__prenom")
    readonly_fields = ("date_creation", "date_modification")


@admin.register(CleAPI)
class CleAPIAdmin(admin.ModelAdmin):
    list_display = (
        "prefixe",
        "partenaire",
        "statut",
        "date_creation",
        "date_revocation",
    )
    list_filter = ("statut",)
    search_fields = ("prefixe", "partenaire__nom_boutique")
    readonly_fields = ("prefixe", "hash_cle", "date_creation", "date_revocation")
