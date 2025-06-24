from django.apps import apps
from django.contrib import admin

admin.site.site_title = "Auto Garden"
admin.site.site_header = "Auto Garden Admin"
admin.site.index_title = "Auto Garden Administration"


def register_all_app_models():
    """
    Register any unregistered app models. We call this function    after registering any custom     admin classes.
     """
    models_to_ignore = [
        'admin.LogEntry',
        'contenttypes.ContentType',
        'sessions.Session',
        'authtoken.TokenProxy',
        'authtoken.Token',  # We automatically register the authtoken app models.
    ]
    for model in apps.get_models():
        try:
            if model._meta.label in models_to_ignore:
                continue
            else:
                class modelAdmin(admin.ModelAdmin):
                    list_display = [field.name for field in model._meta.fields]

                admin.site.register(model, modelAdmin)
        except admin.sites.AlreadyRegistered:
            pass


register_all_app_models()