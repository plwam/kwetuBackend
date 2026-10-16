from django.urls import path

from apps.courses.views import AssignerCourseView, CourseAdminViewSet, DashboardView

urlpatterns = [
    path("admin/dashboard/", DashboardView.as_view()),
    path("admin/courses/", CourseAdminViewSet.as_view({"get": "list"})),
    path("admin/courses/<int:pk>/", CourseAdminViewSet.as_view({"get": "retrieve"})),
    path("admin/courses/<int:pk>/assigner/", AssignerCourseView.as_view()),
]