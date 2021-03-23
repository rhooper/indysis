from django.http import Http404
from filters.mixins import FiltersMixin
from rest_framework import viewsets, serializers, filters
from rest_framework.fields import empty
from rest_framework.response import Response

from sis.studentdb.models import GradeLevel, Student, EmergencyContact, EmergencyContactNumber, StudentHealthConcern, \
    StudentFoodOrder, SchoolYear


class NullToBlankSerializerValidationFixMixin(object):

    def run_validation(self, data=empty):
        for field, value in data.items():
            if not self.fields[field].allow_null and value is None:
                data[field] = ""
        return super(NullToBlankSerializerValidationFixMixin, self).run_validation(data)


class GradeLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeLevel


class GradeLevelNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeLevel
        fields = ('id', 'name', 'name_fr')


class EmergencyContactNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContactNumber
        fields = ('id', 'number', 'ext', 'type', 'primary')


class EmergencyContactNumberWithContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContactNumber
        fields = ('id', 'number', 'ext', 'type', 'primary', 'contact',
                  'is_primary')
    is_primary = serializers.BooleanField(source='primary')


class ActiveStudentSerializer(serializers.ListSerializer):

    def to_representation(self, data):
        data = data.filter(is_active=True, year__isnull=False)
        return super(ActiveStudentSerializer, self).to_representation(data)

    def update(self, instance, validated_data):
        pass


class SiblingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ('id', 'first_name', 'last_name', 'mname', 'year')
        list_serializer_class = ActiveStudentSerializer

    def to_representation(self, instance):
        return super(SiblingSerializer, self).to_representation(instance)


class EmergencyContactSerializer(NullToBlankSerializerValidationFixMixin, serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ('id', 'honorific', 'fname', 'mname', 'lname',
                  'first_name', 'middle_name', 'last_name',
                  'relationship_to_student', 'phones')
    queryset = EmergencyContact.objects.filter(emergency_only=True)
    first_name = serializers.CharField(
        source='fname', allow_blank=True, allow_null=True)
    middle_name = serializers.CharField(
        source='mname', allow_blank=True, allow_null=True, required=False)
    last_name = serializers.CharField(
        source='lname', allow_blank=True, allow_null=True)
    phones = EmergencyContactNumberSerializer(many=True)

    def create(self, validated_data):
        phones = validated_data.pop('phones', None)
        instance = super(EmergencyContactSerializer, self).create(
            validated_data)
        if phones is not None:
            populate_phones(instance, phones)
        return instance

    def update(self, instance, validated_data):
        phones = validated_data.pop('phones', None)
        if phones is not None:
            populate_phones(instance, phones)
        return super(EmergencyContactSerializer, self).update(
            instance, validated_data)


class ParentContactSerializer(NullToBlankSerializerValidationFixMixin, serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ('id', 'honorific', 'fname', 'mname', 'lname',
                  'first_name', 'middle_name', 'last_name',
                  'employer', 'job_title', 'relationship_to_student',
                  'street', 'city', 'state', 'zip', 'postalcode', 'email',
                  'alt_email', 'primary_contact', 'phones',
                  'student_set')
    queryset = EmergencyContact.objects.filter(emergency_only=False)
    phones = EmergencyContactNumberSerializer(many=True)
    student_set = SiblingSerializer(many=True, read_only=True)
    postalcode = serializers.CharField(source='zip')
    first_name = serializers.CharField(
        source='fname', allow_blank=True, allow_null=True)
    middle_name = serializers.CharField(
        source='mname', allow_blank=True, allow_null=True)
    last_name = serializers.CharField(
        source='lname', allow_blank=True, allow_null=True)

    def update(self, instance, validated_data):
        phones = validated_data.pop('phones', None)
        if phones is not None:
            populate_phones(instance, phones)
        return super(ParentContactSerializer, self).update(
            instance, validated_data)


def populate_phones(instance, phones):
    current_phones = set()
    for phone_data in phones:
        try:
            phone = instance.emergencycontactnumber_set.get(
                id=phone_data.pop('id'))
        except KeyError:
            phone = instance.emergencycontactnumber_set.create(**phone_data)
        else:
            for key, value in phone_data.items():
                setattr(phone, key, value)
            phone.save()
        current_phones.add(phone.id)
    for phone in instance.phones:
        if phone.id in current_phones:
            continue
        phone.delete()


class StudentHealthConcernsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentHealthConcern

        fields = ('id', 'type', 'name', 'notes')


class HealthConcernsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentHealthConcern

        fields = ('id', 'type', 'name', 'notes', 'student')


class StudentSerializer(NullToBlankSerializerValidationFixMixin, serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ('id', 'first_name', 'last_name', 'mname', 'middle_name',
                  'sex', 'bday', 'healthcard_no', 'health_card_no',
                  'photo_permission', 'year', 'siblings',
                  'emerg_contacts', 'parents',
                  'health_concerns')
    middle_name = serializers.CharField(
        source='mname', allow_blank=True, allow_null=True)
    siblings = SiblingSerializer(many=True, read_only=True)
    year = GradeLevelSerializer(read_only=True)
    emerg_contacts = EmergencyContactSerializer(many=True, read_only=True)
    parents = ParentContactSerializer(many=True, read_only=True)
    health_concerns = StudentHealthConcernsSerializer(
        many=True, source='studenthealthconcern_set', read_only=True)
    health_card_no = serializers.CharField(source='healthcard_no')


class YearViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A viewset for viewing grade levels.
    """
    serializer_class = GradeLevelSerializer
    queryset = GradeLevel.objects.filter(is_active=True)


class StudentViewSet(FiltersMixin, viewsets.ModelViewSet):
    """
    A viewset for viewing/editing Students and related data.
    """
    serializer_class = StudentSerializer
    queryset = Student.objects.filter(is_active=True)

    filter_mappings = {
        'id': 'id',
    }


class ParentViewSet(FiltersMixin, viewsets.ModelViewSet):
    """
    A viewset for viewing/editing Parents and related data.
    """
    serializer_class = ParentContactSerializer
    queryset = EmergencyContact.objects.filter(student__is_active=True,
                                               emergency_only=False).distinct()
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ('id', 'lname',)
    ordering = ('id',)

    filter_mappings = {
        'id': 'id',
        'email': 'email__iexact',
        'alt_email': 'alt_email__iexact'
    }


class ContactViewSet(FiltersMixin, viewsets.ModelViewSet):
    """
    A viewset for viewing/editing Contacts and related data.
    """
    serializer_class = EmergencyContactSerializer
    queryset = EmergencyContact.objects.filter(student__is_active=True).distinct()
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ('id', )
    ordering = ('id',)

    filter_mappings = {
        'id': 'id',
    }


class PhoneViewSet(FiltersMixin, viewsets.ModelViewSet):
    """
    A viewset for viewing/editing Parents and related data.
    """
    serializer_class = EmergencyContactNumberWithContactSerializer
    queryset = EmergencyContactNumber.objects.filter(contact__student__is_active=True,
                                                     contact__emergency_only=False).distinct()
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ('id', 'type',)
    ordering = ('id',)

    filter_mappings = {
        'id': 'id',
    }



class HealthConcernViewSet(FiltersMixin, viewsets.ModelViewSet):
    """
    A viewset for viewing/editing Contacts and related data.
    """
    serializer_class = HealthConcernsSerializer
    queryset = StudentHealthConcern.objects.filter(student__is_active=True).distinct()
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ('id', )
    ordering = ('id', )

    filter_mappings = {
        'id': 'id',
        'type': 'type',
        'student': 'student__id',
    }


class DictViewSet(viewsets.ViewSet):
    """
    Dictionary View Set
    """
    model = None
    field = None

    @property
    def choices(self):
        return self.get_choices()

    def get_choices(self):
        return dict(self.model._meta.get_field_by_name(self.field)[0].choices)

    def list(self, request):
        return Response(self.choices)

    def retrieve(self, request, pk=None):
        if pk:
            if pk not in self.choices:
                raise Http404("Choice '%s' not found" % pk)
            return Response({pk: self.choices[pk]})
        return Response(self.choices)


class ContactTypeViewSet(DictViewSet):
    """
    List all Contact Types
    """
    model = EmergencyContact
    field = 'relationship_to_student'


class PhoneTypeViewSet(DictViewSet):
    """
    List all Phone Number Types
    """
    model = EmergencyContactNumber
    field = 'type'


class HealthConcernTypeViewSet(DictViewSet):
    """
    List all Health Concern Types
    """
    model = StudentHealthConcern
    field = 'type'


class FoodOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentFoodOrder

    def to_representation(self, obj):
        """Move fields from profile to user representation."""
        representation = super(FoodOrderSerializer, self).to_representation(obj)
        representation['item_name'] = obj.item.item
        representation['item_event'] = obj.item.event.name
        del representation['bulkentry']

        return representation


class FoodOrderViewSet(FiltersMixin, viewsets.ModelViewSet):
    """
    A viewset for viewing/editing Food orders.
    """
    serializer_class = FoodOrderSerializer
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ('id', )
    ordering = ('id', )
    fields = ('id', 'student', 'quantity', 'item')

    def get_queryset(self):

        current_schoolyear = SchoolYear.objects.filter(active_year=True).first()
        queryset = StudentFoodOrder.objects.filter(student__is_active=True, school_year=current_schoolyear,
                                                   item__active=True).distinct()
        return queryset

    filter_mappings = {
        'id': 'id',
        'student': 'student__id',
    }
