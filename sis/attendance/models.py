import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

from sis.studentdb.models import Student, StudentClass, GradeLevel


class AttendanceStatus(models.Model):
    name = models.CharField(max_length=255, unique=True,
                            help_text='"Present" will not be saved but may show as a teacher option.')
    code = models.CharField(max_length=10, unique=True,
                            help_text="Short code used on attendance reports. Ex: A might be the code for the name Absent")
    teacher_selectable = models.BooleanField(default=False, )
    excused = models.BooleanField(default=False, )
    absent = models.BooleanField(default=False,
                                 help_text="Some statistics need to add various types of absent statuses, such as the number in parentheses in daily attendance.")
    tardy = models.BooleanField(default=False,
                                help_text="Some statistics need to add various types of tardy statuses, such as the number in parentheses in daily attendance.")
    half = models.BooleanField(default=False,
                               help_text="Half attendance when counting. DO NOT check off absent otherwise it will double count!")
    order = models.IntegerField(blank=True, null=True, default=1)

    class Meta:
        verbose_name_plural = 'Attendance statuses'
        ordering = ('order',)

    def __str__(self):
        return str(self.name)


class StudentAttendance(models.Model):
    student = models.ForeignKey(Student, related_name="student_attn",
                                help_text="Start typing a student's first or last name to search",
                                on_delete=models.CASCADE)
    recorded_by = models.ForeignKey(User, related_name='student_attn_recorder', blank=True, null=True,
                                    on_delete=models.SET_NULL)
    date = models.DateField(default=datetime.datetime.now, validators=settings.DATE_VALIDATORS)
    status = models.ForeignKey(AttendanceStatus, on_delete=models.CASCADE)
    time = models.TimeField(blank=True, null=True)
    notes = models.CharField(max_length=500, blank=True)
    private_notes = models.CharField(max_length=500, blank=True)

    class Meta:
        unique_together = (("student", "date", 'status'),)
        ordering = ('-date', 'student',)
        permissions = (
            ('take_studentattendance', 'Take student attendance'),
            ('admin_studentattendance', 'Administer student attendance'),
        )

    def __str__(self):
        return str(self.student) + " " + str(self.date) + " " + str(self.status)

    @property
    def edit(self):
        return "Edit"

    def save(self, *args, **kwargs):
        """Don't save Present """
        present, created = AttendanceStatus.objects.get_or_create(name="Present")
        if self.status != present:
            super(StudentAttendance, self).save(*args, **kwargs)
        else:
            try:
                self.delete()
            except:
                pass


class OfficeAttendanceLog(models.Model):
    date = models.DateField(default=datetime.date.today, validators=settings.DATE_VALIDATORS)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    student_class = models.ForeignKey(StudentClass, on_delete=models.CASCADE)
    ampm = models.CharField(
        max_length=4, blank=True, choices=(('am', 'am'), ('pm', 'pm')))

    def __str__(self):
        return str(self.user) + " " + str(self.date) + self.ampm

    class Meta:
        unique_together = ('date', 'student_class', 'ampm')
