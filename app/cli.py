import getpass
from app.extensions import db
from app.models import User


def register_cli(app):
    @app.cli.command("create-admin")
    def create_admin():
        """Create an admin user (email + password)."""

        email = input("Email: ").strip().lower()
        if not email:
            print("Email requerido.")
            return

        if User.query.filter_by(email=email).first():
            print("Ya existe un usuario con ese email.")
            return

        pw1 = getpass.getpass("Password: ")
        pw2 = getpass.getpass("Confirm: ")

        if pw1 != pw2:
            print("No coincide.")
            return

        if len(pw1) < 6:
            print("Password muy corta (min 6).")
            return

        user = User(email=email)
        user.set_password(pw1)

        db.session.add(user)
        db.session.commit()

        print("Admin creado OK.")
