from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length

from datetime import datetime
from wtforms import IntegerField, SelectField, DateTimeLocalField
from wtforms.validators import Optional, NumberRange, ValidationError

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=128)])
    submit = SubmitField("Entrar")

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange

class EventForm(FlaskForm):
    title = StringField("Título", validators=[DataRequired(), Length(max=120)])
    category = SelectField(
        "Categoría",
        choices=[("class", "Clase"), ("tournament", "Torneo"), ("open_play", "Juego libre")],
        validators=[DataRequired()],
    )
    pricing_mode = SelectField(
        "Modo",
        choices=[("PACKAGE", "Paquete (evento completo)"), ("PER_OCCURRENCE", "Por sesión (elige sesiones)")],
        validators=[DataRequired()],
    )
    price = IntegerField("Precio (CLP)", validators=[DataRequired(), NumberRange(min=0)])
    capacity = IntegerField("Cupo del evento (PACKAGE)", validators=[DataRequired(), NumberRange(min=1, max=9999)])
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

        if self.pricing_mode.data == "PER_OCCURRENCE" and self.capacity.data:
            # no es error fatal, pero conceptualmente no se usa
            self.capacity.errors.append(
                "El cupo del evento no se utiliza en eventos por sesión."
            )
            return False

        return True


class OccurrenceForm(FlaskForm):
    start_dt = DateTimeLocalField("Inicio", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    end_dt = DateTimeLocalField("Fin", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])

    capacity = IntegerField("Cupo (solo si PICK_OCCURRENCES)", validators=[Optional(), NumberRange(min=1, max=9999)])

    submit = SubmitField("Guardar")

    def validate(self, extra_validators=None):
        rv = super().validate(extra_validators=extra_validators)
        if not rv:
            return False

        if self.end_dt.data <= self.start_dt.data:
            self.end_dt.errors.append("Fin debe ser posterior al inicio.")
            return False

        return True