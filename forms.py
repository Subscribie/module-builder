from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    FloatField,
    FieldList,
    validators,
    BooleanField,
    TextAreaField,
)
from wtforms.validators import DataRequired


class StripWhitespaceForm(FlaskForm):
    class Meta:
        def bind_field(self, form, unbound_field, options):
            filters = unbound_field.kwargs.get("filters", [])
            if unbound_field.field_class is not FieldList:
                filters.append(strip_whitespace)
            return unbound_field.bind(form=form, filters=filters, **options)


def strip_whitespace(value):
    if value is not None and hasattr(value, "strip"):
        return value.strip()
    return value


class SignupForm(StripWhitespaceForm):
    email = StringField("Email", [validators.Email(), validators.DataRequired()])
    password = StringField("password", validators=[DataRequired()])
    title = FieldList(
        StringField("Title", [validators.DataRequired()]), min_entries=1
    )  # noqa: E501
    company_name = StringField("Company Name")
    slogan = StringField("Slogan")
    instant_payment = FieldList(
        BooleanField("Up-Front Payment", default=False), min_entries=1
    )
    uuid = FieldList(StringField(), min_entries=1)
    subscription = FieldList(
        BooleanField("Subscription", default=False), min_entries=1
    )  # noqa: E501
    note_to_seller_required = FieldList(
        BooleanField("Require note from customer", default=False),
        min_entries=1,  # noqa: E501
    )
    # Allow seller to say what additional information they need
    note_to_buyer_message = FieldList(
        TextAreaField(
            u"Note to buyer",
            [validators.optional(), validators.length(max=500)],  # noqa: E501
        )
    )
    days_before_first_charge = FieldList(
        StringField("Days before first charge")
    )  # noqa: E501
    sell_price = FieldList(
        FloatField("Up-front Price", [validators.optional()]), min_entries=1
    )
    interval_amount = FieldList(
        FloatField("Reccuring Amount", [validators.optional()]), min_entries=1
    )
    interval_unit = FieldList(
        StringField("Interval Unit", [validators.optional()]), min_entries=1
    )
    description = FieldList(
        StringField("Interval Unit", [validators.optional()]), min_entries=1
    )
