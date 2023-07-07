# Composearch

Composearch is a price comparison web app that combines the functionalities of a web scraper and a meta search engine. It allows you to search for products using either a product code or a keyword. Composearch utilizes its integrated web scraping capabilities to crawl and extract data from a predefined list of online stores. The application then presents the search results in a user-friendly table format, sorted by price for convenient comparison.

<img src="/composearch.png" width=75% alt="Composearch Preview"/>

You can see it up and running, deployed on Railway: https://composearch.up.railway.app

## Technologies Used

- **Python**: Powers the backend functionality of Composearch.
- **Django**: Provides a robust framework for building the web application.
- **PostgreSQL**: Stores and manages distributor data, integrated via psycopg 3.
- **Playwright**: Enables efficient web scraping and data extraction from online stores.
- **BeautifulSoup**: Facilitates HTML parsing and data extraction from web pages.
- **Redis**: Implements cache-aside (lazy loading) strategy for improved performance.
- **TailwindCSS**: Enhances the visual aesthetics and responsiveness of the application.
- **Poetry**: Manages the project's dependencies and package management.

## Test Coverage Report

| Name | Stmts | Miss | Cover |
|------|-------|------|-------|
| composearch\\_\_init\_\_.py | 0 | 0 | 100% |
| composearch\settings.py | 35 | 4 | 89% |
| search\\_\_init\_\_.py | 0 | 0 | 100% |
| search\admin.py | 9 | 2 | 78% |
| search\apps.py | 4 | 0 | 100% |
| search\helpers.py | 10 | 0 | 100% |
| search\migrations\0001_initial.py | 5 | 0 | 100% |
| search\migrations\0002_distributorsourcemodel_product_currency_selector.py | 4 | 0 | 100% |
| search\migrations\0003_remove_distributorsourcemodel_product_currency_selector_and_more.py | 4 | 0 | 100% |
| search\migrations\0004_distributorsourcemodel_active.py | 4 | 0 | 100% |
| search\migrations\0005_remove_distributorsourcemodel_including_vat_and_more.py | 4 | 0 | 100% |
| search\migrations\\_\_init\_\_.py | 0 | 0 | 100% |
| search\models.py | 14 | 0 | 100% |
| search\parser.py | 88 | 8 | 91% |
| search\product.py | 53 | 0 | 100% |
| search\search.py | 54 | 0 | 100% |
| search\tests\\_\_init\_\_.py | 0 | 0 | 100% |
| search\tests\fixtures\playwright.py | 47 | 4 | 91% |
| search\tests\fixtures\products.py | 5 | 0 | 100% |
| search\tests\test_distributors.py | 9 | 0 | 100% |
| search\tests\test_fetch_result.py | 29 | 0 | 100% |
| search\tests\test_helpers.py | 15 | 0 | 100% |
| search\tests\test_models.py | 48 | 0 | 100% |
| search\tests\test_parse_html.py | 40 | 0 | 100% |
| search\tests\test_parser.py | 53 | 1 | 98% |
| search\tests\test_perform_search.py | 16 | 0 | 100% |
| **TOTAL** | **550** | **19** | **97%** |

## Quick Start

##### Prerequisites

- Python 3.9+
- Poetry
- Redis (optional)
- PostgreSQL (optional)

##### 1. Checkout the project from github

```
git checkout https://github.com/enev13/composearch.git
```

##### 2. Rename .env.sample file in the project folder to .env and edit the environemnt variables if necessary.

```
mv .env.sample .env
nano .env
```

##### 3. Install the project dependencies

```
poetry install
```

##### 4. Initialize Playwright (it will install Chromium and other dependencies)

```
playwright install --with-deps chromium
```

##### 5. Initialize the Django app

```
python manage.py migrate
python manage.py collectstatic
python manage.py createsuperuser
python manage.py runserver
```

##### 6. Fill in some Distributor data

by either creating new database entries using Django admin

```
http://127.0.0.1:8000/admin
```

or by loading the supplied fixtures file
```
python manage.py loaddata distributors.json
```

(See more details below about the Distributor data format.)

##### 7. Open Composearch in your web browser

```
http://127.0.0.1:8000/
```

## The DistributorSourceModel

In order to have a fully functional app, the database must be populated with distributor data.
For each online store following data is needed:

- name - name of the distributor, e.g. _BestParts_
- base_url - base url with trailing slash, e.g. *https://www.bestparts.com/*
- search_string - the rest of the search address, e.g. *search?q=%s* , where %s is in the place of the search term
- currency - the currency in which the distributor's site operate, e.g. EUR, USD, GBP, etc.
- included_vat - the VAT percentage included in the price. Used to calculate the net price, which will be displayed
- product_name_selector - CSS selector for the product name in the search results
- product_url_selector - CSS selector for the product url in the search results
- product_picture_url_selector - CSS selector for the ulr of the product picture in the search results
- product_price_selector - CSS selector for the product price in the search results
- active - indicates whether this distributor will be used in the searches

## Further Reading

- Playwright Documentation: https://playwright.dev/python/docs/intro
- BeautifulSoup Documentation: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- How to Use CSS Selectors: https://www.w3schools.com/cssref/css_selectors.php
- Using Caching in Django: https://docs.djangoproject.com/en/4.2/topics/cache/#basic-usage

## License

Composearch is released under the [MIT License](/LICENSE). Feel free to use, modify, and distribute the code as per the terms.
