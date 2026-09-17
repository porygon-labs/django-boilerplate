import ast
import keyword
import re
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

SEGMENT = re.compile(r"^[a-z_][a-z0-9_]*$")

APPS_TEMPLATE = """from django.apps import AppConfig


class {config}(AppConfig):
    name = "modules.{module}"
"""

MODEL_TEMPLATE = """from django.db import models


class {model}(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
"""

ADMIN_TEMPLATE = """from django.contrib import admin
from unfold.admin import ModelAdmin

from {model_import} import {model}


@admin.register({model})
class {model}Admin(ModelAdmin):
    list_display = ("name", "created_at", "updated_at")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")
"""

TEST_TEMPLATE = """from django.test import TestCase

from {model_import} import {model}


class {model}Tests(TestCase):
    def test_str_returns_name(self):
        self.assertEqual(str({model}(name="Example")), "Example")
"""


def parse_name(name):
    """Split a name into (module, folders, entity); a trailing separator means no entity."""
    is_folder = name[-1:] in (".", "/")
    segments = re.split(r"[./]", name[:-1] if is_folder else name)
    for segment in segments:
        if not SEGMENT.match(segment) or keyword.iskeyword(segment):
            raise CommandError(
                f"Invalid name {name!r}: each part must be snake_case "
                "(lowercase letters, digits, underscores) and not a Python keyword."
            )
    module, path = segments[0], segments[1:]
    if is_folder:
        return module, path, None
    return module, path[:-1], (path or [module])[-1]


def class_name(segment):
    return "".join(part.capitalize() for part in segment.split("_"))


def write(path, text):
    # Always write LF endings so Windows runs don't rewrite whole files as CRLF.
    path.write_text(text, encoding="utf-8", newline="\n")


def check_directory(path, base_dir):
    file = path.with_suffix(".py")
    if file.exists():
        raise CommandError(
            f"{file.relative_to(base_dir).as_posix()} is a file, but {path.name} must be a directory."
        )
    if path.exists() and not path.is_dir():
        raise CommandError(f"{path.relative_to(base_dir).as_posix()} is not a directory.")


def ensure_package(path, created):
    if not path.exists():
        path.mkdir()
        created.append(path)
    init = path / "__init__.py"
    if not init.exists():
        init.touch()
        created.append(init)


def export(init_file, import_path, symbol):
    """Add `from import_path import symbol` and list symbol in __all__."""
    source = init_file.read_text(encoding="utf-8")
    import_line = f"from {import_path} import {symbol}"
    if not source.strip():
        write(init_file, f'{import_line}\n\n__all__ = [\n    "{symbol}",\n]\n')
        return

    tree = ast.parse(source)
    lines = source.splitlines()
    names = []
    all_node = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            all_node = node
            names = list(ast.literal_eval(node.value))

    names.append(symbol)
    all_block = ["__all__ = ["] + [f'    "{n}",' for n in names] + ["]"]
    if all_node:
        lines[all_node.lineno - 1 : all_node.end_lineno] = all_block
    else:
        lines += ["", *all_block]

    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    position = imports[-1].end_lineno if imports else 0
    lines.insert(position, import_line)
    write(init_file, "\n".join(lines) + "\n")


def exported_names(init_file):
    tree = ast.parse(init_file.read_text(encoding="utf-8"))
    return {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }


def register_app(settings_file, module):
    """Insert the module after the last modules.* entry in INSTALLED_APPS."""
    entry = f'"modules.{module}"'
    source = settings_file.read_text(encoding="utf-8")
    if entry in source:
        return False
    matches = list(re.finditer(r'^(\s*)"modules\.[\w.]+",[^\n]*\n', source, re.M))
    if not matches:
        raise CommandError(
            f"Could not find INSTALLED_APPS modules in {settings_file}. "
            f"Add {entry} manually."
        )
    last = matches[-1]
    line = f"{last.group(1)}{entry},\n"
    write(settings_file, source[: last.end()] + line + source[last.end() :])
    return True


def make_module(name, base_dir):
    module, folders, entity = parse_name(name)
    module_dir = base_dir / "modules" / module
    is_new = not module_dir.exists()

    # Validate everything before writing, so a failed run leaves no partial files.
    check_directory(module_dir, base_dir)
    existing = apps.app_configs.get(module)
    if existing and existing.name != f"modules.{module}":
        raise CommandError(f"App label {module!r} is already used by {existing.name}.")
    for package in ("models", "admin", "tests"):
        current = module_dir / package
        check_directory(current, base_dir)
        for folder in folders:
            current = current / folder
            check_directory(current, base_dir)

    if entity is None:
        target = module_dir.joinpath("models", *folders) if folders else module_dir
        if target.exists():
            raise CommandError(f"{target.relative_to(base_dir).as_posix()} already exists.")
    else:
        check_new_model(module_dir, folders, entity, base_dir)

    created = []
    if is_new:
        module_dir.mkdir(parents=True)
        (module_dir / "__init__.py").touch()
        write(
            module_dir / "apps.py",
            APPS_TEMPLATE.format(config=f"{class_name(module)}Config", module=module)
        )
        created += [module_dir / "__init__.py", module_dir / "apps.py"]
        for package in ("migrations", "views"):
            ensure_package(module_dir / package, created)
    for package in ("models", "admin", "tests"):
        current = module_dir / package
        ensure_package(current, created)
        for folder in folders:
            current = current / folder
            ensure_package(current, created)

    model = None
    if entity is not None:
        model = class_name(entity)
        created += write_model(module, module_dir, folders, entity, model)

    registered = register_app(base_dir / "app" / "settings.py", module)
    return module, model, [p.relative_to(base_dir).as_posix() for p in created], registered


def check_new_model(module_dir, folders, entity, base_dir):
    model_file = module_dir / "models" / Path(*folders, f"{entity}.py")
    admin_file = module_dir / "admin" / Path(*folders, f"{entity}.py")
    test_file = module_dir / "tests" / Path(*folders, f"test_{entity}.py")
    for target in (model_file, model_file.with_suffix(""), admin_file, test_file):
        if target.exists():
            raise CommandError(f"{target.relative_to(base_dir).as_posix()} already exists.")
    models_init = module_dir / "models" / "__init__.py"
    model = class_name(entity)
    if models_init.exists() and model in exported_names(models_init):
        raise CommandError(f"{models_init.relative_to(base_dir).as_posix()} already exports {model}.")


def write_model(module, module_dir, folders, entity, model):
    dotted = ".".join([*folders, entity])
    model_file = module_dir / "models" / Path(*folders, f"{entity}.py")
    admin_file = module_dir / "admin" / Path(*folders, f"{entity}.py")
    test_file = module_dir / "tests" / Path(*folders, f"test_{entity}.py")

    model_import = f"modules.{module}.models.{dotted}"
    context = {"model": model, "model_import": model_import}
    write(model_file, MODEL_TEMPLATE.format(**context))
    write(admin_file, ADMIN_TEMPLATE.format(**context))
    write(test_file, TEST_TEMPLATE.format(**context))

    export(module_dir / "models" / "__init__.py", model_import, model)
    export(
        module_dir / "admin" / "__init__.py",
        f"modules.{module}.admin.{dotted}",
        f"{model}Admin",
    )
    return [model_file, admin_file, test_file]


class Command(BaseCommand):
    help = (
        "Create a module under modules/ (if missing) with a model, admin, and test. "
        "Examples: shop, shop.product, shop/order/invoice. "
        "End the name with . or / to create a folder only: shop.catalog., payment/"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "name",
            help="module[.folder...].model, separated by . or /; trailing separator = folder",
        )

    def handle(self, *args, name, **options):
        module, model, created, registered = make_module(
            name, Path(settings.BASE_DIR)
        )
        for path in created:
            self.stdout.write(f"  created  {path}")
        if registered:
            self.stdout.write(f'  updated  app/settings.py (added "modules.{module}")')
        if model is None:
            folder = re.sub(r"[./]", "/", name.rstrip("./")).partition("/")[2]
            where = f"folder {folder}/ in modules.{module}" if folder else f"modules.{module}"
            self.stdout.write(self.style.SUCCESS(f"Created {where}."))
            return
        self.stdout.write(
            self.style.SUCCESS(f"Created {model} in modules.{module}.")
            + "\nNext: add fields to the model, then run "
            "`make makemigrations` and `make migrate`."
        )
