from django.urls import path

from apps.drivers.views import (
    VueAccepterCourse,
    VueCocherPaye,
    VueCoursesDisponibles,
    VueCoursesEnCours,
    VueHistoriqueJour,
    VueLivreurDashboard,
    VueLivrerAvecCode,
    VueMarquerRecupere,
)

app_name = "drivers"

urlpatterns = [
    path("dashboard/", VueLivreurDashboard.as_view(), name="dashboard"),
    path("courses/disponibles/", VueCoursesDisponibles.as_view(),
         name="courses-disponibles"),
    path("courses/en-cours/", VueCoursesEnCours.as_view(),
         name="courses-en-cours"),
    path("courses/<int:pk>/accepter/", VueAccepterCourse.as_view(),
          name="accepter"),
    path("courses/<int:pk>/recuperer/", VueMarquerRecupere.as_view(),
         name="recuperer"),
    path("courses/<int:pk>/livrer/", VueLivrerAvecCode.as_view(),
         name="livrer"),
    path("courses/<int:pk>/payer/", VueCocherPaye.as_view(),
         name="payer"),
    path("historique/", VueHistoriqueJour.as_view(),
         name="historique"),
]