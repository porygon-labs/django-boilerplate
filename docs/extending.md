# Extend the Boilerplate

Feature code lives under `modules/`.
Each Django module uses packages instead of growing large `models.py`, `views.py`, `admin.py`, or `tests.py` files.

This tutorial adds a `shop` module that lists available products.

## 1. Create the Module

Run:

```sh
make module shop.product
```

The name is `<module>.<model>`, and `.` and `/` both work as separators.
Running `make module shop` alone creates the module with a model named after it (`Shop`).
Run `make module` without a name to print more examples.

The command creates the module when it does not exist yet:

```text
modules/shop/
├── admin/
│   ├── __init__.py      # exports ProductAdmin
│   └── product.py
├── migrations/
│   └── __init__.py
├── models/
│   ├── __init__.py      # exports Product
│   └── product.py
├── tests/
│   ├── __init__.py
│   └── test_product.py
├── views/
│   └── __init__.py
├── __init__.py
└── apps.py
```

It also adds `"modules.shop"` to `INSTALLED_APPS` after the other `modules.*` entries, so `django_cleanup.apps.CleanupConfig` stays last.

The command refuses to overwrite files, so it fails when the model already exists.

## 2. Add More Models

Run the command again with the same module name:

```sh
make module shop.catalog.category
make module shop/order/invoice
```

Nested names become subpackages of the same Django app, not separate apps:

```text
modules/shop/models/
├── __init__.py          # exports Product, Category, Invoice
├── catalog/
│   ├── __init__.py
│   └── category.py
├── order/
│   ├── __init__.py
│   └── invoice.py
└── product.py
```

`admin/` and `tests/` get the same layout.

End the name with `.` or `/` to create only a folder, without a model:

```sh
make module shop.catalog.   # same as shop/catalog/
make module payment/        # module without any model
```

The command creates missing folders automatically when you add a nested model, so you only need this for an empty folder.
Every model still belongs to the `shop` app label, so the `Invoice` table is `shop_invoice`.
Class names must be unique within a module.
A name can't be both a model file and a folder.
If `models/order.py` already exists, `shop.order.` and `shop.order.invoice` both fail.
Move the model into `models/order/order.py` and fix its imports first.

## 3. Define the Model

The generated `modules/shop/models/product.py` has a `name` field and timestamps.
Add the fields you need:

```python
from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
```

Create and apply migrations:

```sh
make makemigrations
make migrate
```

Commit generated migrations.
Never edit migrations already applied in shared or production environments.

## 4. Adjust Admin Management

Update `modules/shop/admin/product.py` to match the new fields:

```python
from django.contrib import admin
from unfold.admin import ModelAdmin

from modules.shop.models.product import Product


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ("name", "price", "is_available", "created_at")
    list_filter = ("is_available",)
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")
```

## 5. Add a View

Create `modules/shop/views/product.py`:

```python
from django.shortcuts import render

from modules.shop.models.product import Product


def product_list(request):
    products = Product.objects.filter(is_available=True).order_by("name")
    return render(request, "shop/product_list.html", {"products": products})
```

Export the view from `modules/shop/views/__init__.py`:

```python
from modules.shop.views.product import product_list
```

## 6. Add URLs

Create `modules/shop/urls.py`:

```python
from django.urls import path

from modules.shop.views import product_list

app_name = "shop"

urlpatterns = [
    path("", product_list, name="product-list"),
]
```

Include it from `app/urls.py`:

```python
urlpatterns = [
    path("shop/", include("modules.shop.urls")),
    path("", admin.site.urls),
]
```

Keep feature URLs before the root admin route because Django admin has a final catch-all view.

## 7. Add a Template

Create `modules/shop/templates/shop/product_list.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Shop</title>
  </head>
  <body>
    <main>
      <h1>Shop</h1>
      {% for product in products %}
        <article>
          <h2>{{ product.name }}</h2>
          <p>{{ product.price }}</p>
          <p>{{ product.description }}</p>
        </article>
      {% empty %}
        <p>No products available.</p>
      {% endfor %}
    </main>
  </body>
</html>
```

## 8. Add Tests

The generated `tests/test_product.py` only checks `__str__`.
Add behavior tests next to it, for example `modules/shop/tests/test_product_list.py`:

```python
from django.test import TestCase
from django.urls import reverse

from modules.shop.models.product import Product


class ProductListTests(TestCase):
    def test_shows_only_available_products(self):
        Product.objects.create(name="Keyboard", price="49.00", is_available=True)
        Product.objects.create(name="Monitor", price="199.00", is_available=False)

        response = self.client.get(reverse("shop:product-list"))

        self.assertContains(response, "Keyboard")
        self.assertNotContains(response, "Monitor")
```

Test modules do not need exports in `tests/__init__.py`.

Run:

```sh
make test
make check
```

## 9. Grow Packages Safely

Use one file per cohesive concept, not automatically one file per class.
Group related models into folders once a module has several of them.

Example:

```text
modules/shop/
├── admin/
│   ├── __init__.py
│   ├── catalog/
│   │   ├── __init__.py
│   │   └── category.py
│   └── product.py
├── models/
│   ├── __init__.py
│   ├── catalog/
│   │   ├── __init__.py
│   │   └── category.py
│   └── product.py
├── tests/
│   ├── __init__.py
│   ├── catalog/
│   │   ├── __init__.py
│   │   └── test_category.py
│   ├── test_product.py
│   └── test_product_list.py
└── views/
    ├── __init__.py
    ├── category.py
    └── product.py
```

`make module` exports models and admin registrations for you.
Export public views from `views/__init__.py` yourself.
Avoid empty `services/`, `selectors/`, or `repositories/` packages until feature code needs those boundaries.

## 10. Deploy

Build and recreate services:

```sh
docker compose up --build -d
```

Container startup applies committed migrations and collects static files before Gunicorn starts.

Verify the release:

```sh
docker compose exec web .venv/bin/python manage.py check --deploy
docker compose logs web
```

See [deployment.md](deployment.md) for HTTPS, updates, and backups.

## Feature Checklist

- Module lives under `modules/`.
- Module is registered before `django_cleanup.apps.CleanupConfig` (done by `make module`).
- Models are exported from `models/__init__.py`.
- Admin modules are imported from `admin/__init__.py`.
- Model changes include generated migrations.
- Feature URLs are included by `app/urls.py`.
- User-visible behavior has tests under `tests/`.
- New environment variables are documented in `.env.example`.
- `make test` and `make check` pass.
