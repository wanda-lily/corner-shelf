from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, TextAreaField, IntegerField,
    SelectField, URLField, DateTimeLocalField, HiddenField, BooleanField,
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, NumberRange,
    Optional, URL, ValidationError
)
from models.enums import ShelfType, ShelfRole, ReadingStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enum_choices(enum_cls):
    """Turn an enum into a list of (value, label) pairs for SelectField."""
    return [(e.value, e.value.replace("_", " ").title()) for e in enum_cls]


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class RegistrationForm(FlaskForm):
    """New account sign-up."""
    name = StringField("Name",
                       validators=[DataRequired(), Length(max=50)])
    email = StringField("Email",
                        validators=[DataRequired(), Email(), Length(max=100)])
    password = PasswordField("Password",
                             validators=[DataRequired(), Length(min=8)])
    confirm = PasswordField("Confirm Password",
                            validators=[DataRequired(), EqualTo("password",
                                                                message="Passwords must match.")])


class LoginForm(FlaskForm):
    email = StringField("Email",
                        validators=[DataRequired(), Email()])
    password = PasswordField("Password",
                             validators=[DataRequired()])
    remember = BooleanField("Remember Me")


class EditProfileForm(FlaskForm):
    """Change display name or email — password handled separately."""
    name = StringField("Name",
                       validators=[DataRequired(), Length(max=50)])
    email = StringField("Email",
                        validators=[DataRequired(), Email(), Length(max=100)])


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password",
                                     validators=[DataRequired()])
    new_password = PasswordField("New Password",
                                 validators=[DataRequired(), Length(min=8)])
    confirm = PasswordField("Confirm New Password",
                            validators=[DataRequired(),
                                        EqualTo("new_password",
                                                message="Passwords must match.")])


# ---------------------------------------------------------------------------
# Tag
# ---------------------------------------------------------------------------

class TagForm(FlaskForm):
    name = StringField("Tag Name",
                       validators=[DataRequired(), Length(max=50)])


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------

class SearchBookForm(FlaskForm):
    """
    For adding books from google's book api
    """
    search = StringField("Title",
                         validators=[DataRequired(), Length(max=200)])


class BookForm(FlaskForm):
    """
    Used when manually adding a book (as opposed to importing from Google Books).
    google_books_id is optional — leave blank for manual entries.
    """
    title = StringField("Title",
                        validators=[DataRequired(), Length(max=200)])
    author = StringField("Author",
                         validators=[Optional(), Length(max=100)])
    cover_url = URLField("Cover Image URL",
                         validators=[Optional(), URL(), Length(max=500)])
    description = TextAreaField("Description",
                                validators=[Optional()])
    google_books_id = StringField("Google Books ID",
                                  validators=[Optional(), Length(max=20)])
    total_pages = IntegerField("Total Pages",
                               validators=[Optional(), NumberRange(min=1)])


# ---------------------------------------------------------------------------
# Shelf
# ---------------------------------------------------------------------------

class ShelfForm(FlaskForm):
    name = StringField("Shelf Name",
                       validators=[DataRequired(), Length(max=100)])
    shelf_type = SelectField("Type",
                             choices=_enum_choices(ShelfType),
                             default=ShelfType.personal.value)


# ---------------------------------------------------------------------------
# ShelfEntry  (adding a book to a shelf)
# ---------------------------------------------------------------------------

class ShelfEntryForm(FlaskForm):
    """
    book_id and shelf_id are typically pre-filled from the route context
    (e.g. /shelves/<shelf_id>/add/<book_id>), so they use HiddenField.
    Expose them as visible selects if your UI requires manual selection.
    """
    shelf_id = HiddenField("Shelf",
                           validators=[DataRequired()])
    book_id = HiddenField("Book",
                          validators=[DataRequired()])
    notes = TextAreaField("Notes",
                          validators=[Optional()])


# ---------------------------------------------------------------------------
# ReadingLog
# ---------------------------------------------------------------------------

class ReadingLogForm(FlaskForm):
    """
    book_id is hidden — set from route context.
    Users fill in their reading state; user_id comes from current_user.
    """
    book_id = HiddenField("Book",
                          validators=[DataRequired()])
    status = SelectField("Status",
                         choices=_enum_choices(ReadingStatus),
                         default=ReadingStatus.want_to_read.value)
    rating = SelectField("Rating",
                         choices=[("", "— no rating —")] +
                         [(str(i), "★" * i) for i in range(1, 6)],
                         default="",
                         validators=[Optional()])
    progress_pages = IntegerField("Pages Read",
                                  validators=[Optional(), NumberRange(min=0)])
    started_at = DateTimeLocalField("Started",
                                    format="%Y-%m-%dT%H:%M",
                                    validators=[Optional()])
    finished_at = DateTimeLocalField("Finished",
                                     format="%Y-%m-%dT%H:%M",
                                     validators=[Optional()])

    def validate_rating(self, field):
        """Convert empty string to None; reject out-of-range values."""
        if field.data == "" or field.data is None:
            field.data = None
            return
        try:
            val = int(field.data)
        except (TypeError, ValueError):
            raise ValidationError("Rating must be a number between 1 and 5.")
        if not (1 <= val <= 5):
            raise ValidationError("Rating must be between 1 and 5.")
        field.data = val

    def validate_finished_at(self, field):
        if field.data and self.started_at.data:
            if field.data < self.started_at.data:
                raise ValidationError(
                    "Finished date cannot be before started date.")


# ---------------------------------------------------------------------------
# ShelfParticipant  (inviting someone to a shared shelf)
# ---------------------------------------------------------------------------

class ShelfParticipantForm(FlaskForm):
    shelf_id = HiddenField("Shelf",
                           validators=[DataRequired()])
    email = StringField("User Email",
                        validators=[DataRequired(), Email()])
    role = SelectField("Role",
                       choices=_enum_choices(ShelfRole),
                       default=ShelfRole.viewer.value)


class EditParticipantRoleForm(FlaskForm):
    """Change an existing participant's role."""
    role = SelectField("Role",
                       choices=_enum_choices(ShelfRole))


# ---------------------------------------------------------------------------
# BookNote
# ---------------------------------------------------------------------------

class BookNoteForm(FlaskForm):
    book_id = HiddenField("Book",
                          validators=[DataRequired()])
    content = TextAreaField("Note",
                            validators=[DataRequired()])
    page = IntegerField("Page Number",
                        validators=[Optional(), NumberRange(min=1)],
                        description="Optional — which page this note refers to")
