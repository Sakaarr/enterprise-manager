# cars/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import JobEntry, Car
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=JobEntry)
def log_jobentry_save(sender, instance, created, **kwargs):
    if created:
        logger.info(f"New JobEntry created: {instance}")
    else:
        logger.info(f"JobEntry updated: {instance}")

@receiver(post_delete, sender=JobEntry)
def log_jobentry_delete(sender, instance, **kwargs):
    logger.info(f"JobEntry deleted: {instance}")

@receiver(post_save, sender=Car)
def log_car_save(sender, instance, created, **kwargs):
    if created:
        logger.info(f"New Car added: {instance}")
    else:
        logger.info(f"Car updated: {instance}")
