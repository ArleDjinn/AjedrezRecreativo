# app/blueprints/admin/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, SelectField
from wtforms.fields import DateTimeLocalField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=128)])
    submit = SubmitField("Entrar")


class EventForm(FlaskForm):
    title = StringField("Título", validators=[DataRequired(), Length(max=120)])

    pricing_mode = SelectField(
        "Modo",
        choices=[
            ("PACKAGE", "Paquete (todas las sesiones)"),
            ("PER_OCCURRENCE", "Por sesión"),
        ],
        validators=[DataRequired()],
    )

    price = IntegerField("Precio base (CLP)", validators=[DataRequired(), NumberRange(min=0)])

    capacity_default = IntegerField(
        "Cupo por defecto",
        validators=[Optional(), NumberRange(min=1, max=9999)],
    )

    location_name = StringField("Lugar", validators=[DataRequired(), Length(max=120)])

    status = SelectField(
        "Estado",
        choices=[("draft", "Borrador"), ("published", "Publicado"), ("closed", "Cerrado")],
        validators=[DataRequired()],
    )

    submit = SubmitField("Guardar")

    def validate(self, extra_validators=None):
        rv = super().validate(extra_validators)
        if not rv:
            return False

        # Para PACKAGE exigimos cupo por defecto (si no, no puedes calcular disponibilidad).
        if self.pricing_mode.data == "PACKAGE" and not self.capacity_default.data:
            self.capacity_default.errors.append(
                "El cupo por defecto es obligatorio para eventos tipo paquete."
            )
            return False

        return True


class OccurrenceForm(FlaskForm):
    start_dt = DateTimeLocalField("Inicio", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    end_dt = DateTimeLocalField("Fin", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])

    capacity_override = IntegerField(
        "Cupo específico (opcional)",
        validators=[Optional(), NumberRange(min=1, max=9999)],
    )

    price_override = IntegerField(
        "Precio específico (opcional)",
        validators=[Optional(), NumberRange(min=0)],
    )

    submit = SubmitField("Guardar")

    def validate(self, extra_validators=None):
        rv = super().validate(extra_validators=extra_validators)
        if not rv:
            return False

        if self.end_dt.data <= self.start_dt.data:
            self.end_dt.errors.append("Fin debe ser posterior al inicio.")
            return False

        return True