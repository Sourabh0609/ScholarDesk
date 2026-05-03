from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser, Student, Staff


@receiver(post_save, sender=CustomUser)
def create_role_profile(sender, instance, created, **kwargs):
    if created:
        if instance.role == 'student':
            if not hasattr(instance, 'student_profile'):
                Student.objects.get_or_create(
                    user=instance,
                    defaults={'roll_number': f'STU{instance.id:05d}'}
                )
        elif instance.role in ('staff', 'hod'):
            if not hasattr(instance, 'staff_profile'):
                Staff.objects.get_or_create(
                    user=instance,
                    defaults={'employee_id': f'EMP{instance.id:05d}'}
                )