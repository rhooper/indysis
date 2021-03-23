from rest_framework import routers

from api import views

router = routers.DefaultRouter()
router.register(r'level', views.YearViewSet)
router.register(r'student', views.StudentViewSet)
router.register(r'parent', views.ParentViewSet)
router.register(r'contacts', views.ContactViewSet)
router.register(r'health_concerns', views.HealthConcernViewSet)
router.register(r'phones', views.PhoneViewSet)
router.register(r'contact_types', views.ContactTypeViewSet, base_name='contact_type')
router.register(r'phone_types', views.PhoneTypeViewSet, base_name='phone_type')
router.register(r'health_concern_types', views.HealthConcernTypeViewSet, base_name='health_concern_type')
router.register(r'food_orders', views.FoodOrderViewSet, base_name='food_order')
urlpatterns = router.urls
