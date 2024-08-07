import jsonschema

from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType


from .models import ExtensionSchema
from .utils import get_tenant_field, create_form_field, validate_extended_data


class ExtensibleModelAdminMixin:

    def get_form(self, request, obj=None, **kwargs):
        original_kwargs = kwargs.copy()
        if "fields" in original_kwargs:
            original_fields = [
                f
                for f in original_kwargs["fields"]
                if f in [field.name for field in self.model._meta.get_fields()]
            ]
            original_kwargs["fields"] = original_fields

        FormClass = super().get_form(request, obj, **original_kwargs)
        extension_schema = self._get_extension_schema(obj)

        class ExtendedForm(FormClass):
            extended_data = forms.CharField(
                widget=forms.Textarea(attrs={"readonly": "readonly"}),
                required=False,
                help_text="Extended data",
            )

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.extension_schema = extension_schema

                for field_name in original_fields:
                    if field_name not in self.fields:
                        self.fields[field_name] = self.base_fields[field_name]

                if self.extension_schema:
                    for field_name, field_schema in self.extension_schema.schema.get(
                        "properties", {}
                    ).items():
                        self.fields[field_name] = create_form_field(
                            field_name, field_schema
                        )
                        if (
                            self.instance
                            and self.instance.extended_data
                            and field_name in self.instance.extended_data
                        ):
                            self.initial[field_name] = self.instance.extended_data[
                                field_name
                            ]

                for field_name in self.base_fields:
                    if field_name not in self.fields:
                        self.fields[field_name] = self.base_fields[field_name]

            def clean(self):
                cleaned_data = super().clean()
                self.cleaned_extended_data = {}
                missing_required_fields = []
                is_update = self.instance.pk is not None

                # If it's not an update and there's no extension schema, skip everything
                if not is_update and not self.extension_schema:
                    return cleaned_data

                if self.extension_schema:
                    for field_name, field_schema in self.extension_schema.schema.get(
                        "properties", {}
                    ).items():
                        if field_name in self.extension_schema.schema.get(
                            "required", []
                        ) and not cleaned_data.get(field_name):
                            missing_required_fields.append(field_name)
                        if field_name in cleaned_data:
                            value = cleaned_data[field_name]

                            if field_schema.get("type") == "array":
                                # For multi-select fields, an empty list means no selection
                                if isinstance(value, list):
                                    self.cleaned_extended_data[field_name] = value
                                elif value:
                                    self.cleaned_extended_data[field_name] = [value]
                            elif value is not None:
                                self.cleaned_extended_data[field_name] = value

                    if missing_required_fields:
                        raise ValidationError(
                            {
                                field: f"{field} is required."
                                for field in missing_required_fields
                            }
                        )

                    # Validate for both creation and update
                    validate_extended_data(
                        self.cleaned_extended_data,
                        self.extension_schema.schema,
                        is_creation=not is_update,
                    )

                return cleaned_data

        return ExtendedForm

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))

        extension_schema = self._get_extension_schema(obj)
        if extension_schema:
            extended_fields = list(extension_schema.schema.get("properties", {}).keys())
            fieldsets.append(("Extended Fields", {"fields": extended_fields}))

        if obj and obj.extended_data and obj.extended_data != {}:
            fieldsets.append(
                ("Meta", {"fields": ["extended_data"], "classes": ("collapse",)})
            )

        return fieldsets

    def _get_extension_schema(self, obj, request=None):
        if obj and hasattr(obj, get_tenant_field()):
            content_type = ContentType.objects.get_for_model(obj.__class__)
            return (
                ExtensionSchema.objects.filter(
                    content_type=content_type,
                    **{get_tenant_field(): getattr(obj, get_tenant_field())},
                )
                .order_by("-version")
                .first()
            )
        elif hasattr(self, "model") and request:
            tenant = self._get_tenant_from_request(request)
            if tenant:
                return self.model.get_latest_schema(tenant)
        return None

    def save_model(self, request, obj, form, change):
        if change:
            # This is an update
            if hasattr(form, "cleaned_extended_data"):
                # Merge the new data with the existing data
                for key, value in form.cleaned_extended_data.items():
                    if value is not None and value != []:
                        obj.extended_data[key] = value
                    elif key in obj.extended_data:
                        # Remove the key if the new value is None or an empty list
                        del obj.extended_data[key]
        else:
            # This is a new object
            if hasattr(form, "cleaned_extended_data"):
                obj.extended_data = {
                    k: v
                    for k, v in form.cleaned_extended_data.items()
                    if v is not None and v != []
                }
            else:
                obj.extended_data = {}

        super().save_model(request, obj, form, change)

    def _get_tenant_from_request(self, request):

        tenant_field = get_tenant_field()

        if hasattr(request, tenant_field):
            return getattr(request, tenant_field)
        if hasattr(request.user, tenant_field):
            return getattr(request.user, tenant_field)

        raise NotImplementedError(
            f"Unable to find '{tenant_field}' in request or user. Implement _get_tenant_from_request in your admin class to handle your specific tenant retrieval logic."
        )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        extension_schema = self._get_extension_schema(
            None
        )  # Pass None as we don't have an object yet

        if extension_schema:
            field_schema = extension_schema.schema.get("properties", {}).get(
                db_field.name, {}
            )
            if field_schema.get("type") == "array" and "items" in field_schema:
                formfield.required = False  # Make array fields non-required
        return formfield

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if obj:
            extension_schema = self._get_extension_schema(obj)
            if extension_schema:
                extended_fields = list(
                    extension_schema.schema.get("properties", {}).keys()
                )
                fields = [
                    f for f in fields if f not in extended_fields
                ] + extended_fields
        return fields

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        return (
            list(readonly_fields) + ["extended_data"]
            if obj and obj.extended_data
            else readonly_fields
        )


class ExtensionSchemaAdmin(admin.ModelAdmin):
    list_display = ("content_type", get_tenant_field(), "version", "created_at")
    list_filter = ("content_type", get_tenant_field())
    readonly_fields = ("version",)

    def save_model(self, request, obj, form, change):
        tenant_field = get_tenant_field()
        if not change:  # New schema
            obj.version = (
                ExtensionSchema.objects.filter(
                    content_type=obj.content_type,
                    **{tenant_field: getattr(obj, tenant_field)},
                ).count()
                + 1
            )
        super().save_model(request, obj, form, change)


admin.site.register(ExtensionSchema, ExtensionSchemaAdmin)
