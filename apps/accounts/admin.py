from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import CleAPI, Livreur, Partenaire, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'nom', 'prenom', 'role', 'actif', 'date_creation')
    list_filter = ('role', 'actif')
    search_fields = ('email', 'nom', 'prenom', 'telephone')
    ordering = ('-date_creation',)
    readonly_fields = ('date_creation', 'date_modification')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informations personnelles', {'fields': ('nom', 'prenom', 'telephone')}),
        ('Permissions', {'fields': ('role', 'actif', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('date_creation', 'date_modification')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nom', 'prenom', 'telephone', 'role', 'password1', 'password2'),
        }),
    )


@admin.register(Partenaire)
class PartenaireAdmin(admin.ModelAdmin):
    list_display = ('nom_boutique', 'user', 'actif', 'date_creation')
    list_filter = ('actif',)
    search_fields = ('nom_boutique', 'user__email', 'user__nom')
    readonly_fields = ('date_creation', 'date_modification')


@admin.register(Livreur)
class LivreurAdmin(admin.ModelAdmin):
    list_display = ('user', 'disponible', 'actif', 'date_creation')
    list_filter = ('disponible', 'actif')
    search_fields = ('user__email', 'user__nom', 'user__prenom')
    readonly_fields = ('date_creation', 'date_modification')


@admin.register(CleAPI)
class CleAPIAdmin(admin.ModelAdmin):
    list_display = ('prefixe', 'partenaire', 'statut', 'date_creation', 'date_revocation')
    list_filter = ('statut',)
    search_fields = ('prefixe', 'partenaire__nom_boutique')
    readonly_fields = ('prefixe', 'hash_cle', 'date_creation', 'date_revocation')