import tempfile
from pathlib import Path

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from modules.core.management.commands.make_module import make_module

SETTINGS = """INSTALLED_APPS = [
    "django.contrib.admin",
    "modules.core",
    "django_cleanup.apps.CleanupConfig",
]
"""


class MakeModuleTests(SimpleTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.base = Path(directory.name)
        (self.base / "app").mkdir()
        (self.base / "modules").mkdir()
        (self.base / "app" / "settings.py").write_text(SETTINGS)

    def read(self, path):
        return (self.base / path).read_text()

    def test_creates_module_with_model_named_after_it(self):
        make_module("movie", self.base)

        movie = self.base / "modules" / "movie"
        for package in ("admin", "migrations", "models", "tests", "views"):
            self.assertTrue((movie / package / "__init__.py").is_file())
        self.assertIn('name = "modules.movie"', self.read("modules/movie/apps.py"))
        self.assertIn("class Movie(models.Model):", self.read("modules/movie/models/movie.py"))
        self.assertTrue((movie / "tests" / "test_movie.py").is_file())
        self.assertEqual(
            self.read("modules/movie/models/__init__.py"),
            'from modules.movie.models.movie import Movie\n\n__all__ = [\n    "Movie",\n]\n',
        )
        self.assertIn(
            '    "modules.core",\n    "modules.movie",\n    "django_cleanup',
            self.read("app/settings.py"),
        )

    def test_adds_models_to_existing_module_with_either_separator(self):
        make_module("movie", self.base)
        make_module("movie.genre", self.base)
        make_module("movie/schedule/cinema_a", self.base)

        self.assertEqual(
            self.read("modules/movie/models/__init__.py"),
            "from modules.movie.models.movie import Movie\n"
            "from modules.movie.models.genre import Genre\n"
            "from modules.movie.models.schedule.cinema_a import CinemaA\n"
            "\n"
            '__all__ = [\n    "Movie",\n    "Genre",\n    "CinemaA",\n]\n',
        )
        self.assertIn(
            "from modules.movie.admin.schedule.cinema_a import CinemaAAdmin",
            self.read("modules/movie/admin/__init__.py"),
        )
        for path in ("models/schedule", "admin/schedule", "tests/schedule"):
            self.assertTrue((self.base / "modules/movie" / path / "__init__.py").is_file())
        self.assertEqual(self.read("app/settings.py").count('"modules.movie"'), 1)

    def test_creates_module_when_first_name_is_nested(self):
        make_module("movie.genre", self.base)

        self.assertFalse((self.base / "modules/movie/models/movie.py").exists())
        self.assertTrue((self.base / "modules/movie/models/genre.py").is_file())

    def test_rejects_existing_model(self):
        make_module("movie.genre", self.base)

        with self.assertRaisesMessage(CommandError, "already exists"):
            make_module("movie/genre", self.base)

    def test_rejects_folder_that_is_a_file(self):
        make_module("movie.schedule", self.base)
        before = sorted(self.base.rglob("*"))

        with self.assertRaisesMessage(CommandError, "must be a directory"):
            make_module("movie/schedule/cinema_a", self.base)
        self.assertEqual(sorted(self.base.rglob("*")), before)

    def test_trailing_separator_creates_folder_without_model(self):
        for name in ("movie/schedule/", "movie.showtime."):
            make_module(name, self.base)

        movie = self.base / "modules" / "movie"
        for package in ("admin", "models", "tests"):
            for folder in ("schedule", "showtime"):
                self.assertTrue((movie / package / folder / "__init__.py").is_file())
        self.assertEqual(self.read("modules/movie/models/__init__.py"), "")
        self.assertFalse((movie / "models" / "movie.py").exists())

        make_module("movie.schedule.genre", self.base)
        self.assertTrue((movie / "models" / "schedule" / "genre.py").is_file())

    def test_trailing_separator_on_module_creates_empty_module(self):
        make_module("movie/", self.base)

        self.assertTrue((self.base / "modules/movie/apps.py").is_file())
        self.assertEqual(list((self.base / "modules/movie/models").iterdir()), [
            self.base / "modules/movie/models/__init__.py"
        ])
        self.assertIn('"modules.movie"', self.read("app/settings.py"))
        with self.assertRaisesMessage(CommandError, "modules/movie already exists"):
            make_module("movie.", self.base)

    def test_rejects_existing_folder(self):
        make_module("movie/schedule/", self.base)

        with self.assertRaisesMessage(CommandError, "already exists"):
            make_module("movie.schedule.", self.base)

    def test_rejects_folder_where_model_file_exists(self):
        make_module("movie.schedule", self.base)

        with self.assertRaisesMessage(CommandError, "must be a directory"):
            make_module("movie.schedule.", self.base)

    def test_rejects_invalid_names(self):
        for name in ("Movie", "movie..genre", "movie//", ".", "movie.class", "movie-genre"):
            with self.subTest(name=name), self.assertRaises(CommandError):
                make_module(name, self.base)

    def test_rejects_label_used_by_another_app(self):
        with self.assertRaisesMessage(CommandError, "django.contrib.auth"):
            make_module("auth", self.base)
