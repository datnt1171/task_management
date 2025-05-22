from django.contrib import admin
from .models import Category, Document, SignatureRequest, SignatureLog

admin.site.register(Category)
admin.site.register(Document)
admin.site.register(SignatureRequest)
admin.site.register(SignatureLog)
