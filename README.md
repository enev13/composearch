# Composearch

Composearch is a price comparison tool that combines the functionalities of a web scraper and a meta search engine. It allows you to search for products using either a product code or a keyword. Composearch utilizes its integrated web scraping capabilities to crawl and extract data from a predefined list of online stores. The application then presents the search results in a user-friendly table format, sorted by price for convenient comparison.

<img src="/composearch.png" width=75% alt="Composearch Preview"/>

# Technologies used

- **Python**: Powers the backend functionality of Composearch.
- **Django**: Provides a robust framework for building the web application.
- **MongoDB**: Stores and manages distributor data, integrated via Djongo/PyMongo.
- **Playwright**: Enables efficient web scraping and data extraction from online stores.
- **BeautifulSoup**: Facilitates HTML parsing and data extraction from web pages.
- **TailwindCSS**: Enhances the visual aesthetics and responsiveness of the application.
- **Poetry**: Manages the project's dependencies and package management.

# Prerequisites

- Python 3.11
- Poetry
- MongoDB Atlas account with a cluster

# Quick Start

1. Checkout the project from github

```
git checkout https://github.com/enev13/composearch.git
```

2. Create .env file in the project folder...

```
touch .env
```

... and fill it with following environemnt variables:

```
# Django debug mode
DEBUG=True
# Django secret key string
SECRET_KEY=not_so_secret_key_qwerty1234
# MongoDB Atlas connection string
MONGO_HOST=mongodb+srv://<username>:<password>@<atlas cluster>/<myFirstDatabase>?retryWrites=true&w=majority
```

3. Install the project dependencies

```
poetry install
```

4. Initialize Playwright (it will install its required browsers)

```
playwright install
```

5. Initialize the Django app

```
python manage.py migrate
python manage.py collectstatic
python manage.py createsuperuser
python manage.py runserver
```

6. Open Django admin in your browser and fill some Distributor data

```
http://127.0.0.1:8000/admin
```

See more details below about the Distributor data that will be needed.

7. Open Composearch in your web browser

```
http://127.0.0.1:8000/
```

# The DistributorSourceModel

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

# Further Reading

- Playwright Documentation: `https://playwright.dev/python/docs/intro`
- BeautifulSoup Documentation: `https://www.crummy.com/software/BeautifulSoup/bs4/doc/`
- How to Use CSS Selectors: `https://www.w3schools.com/cssref/css_selectors.php`

# License

Composearch is released under the [MIT License](/LICENSE). Feel free to use, modify, and distribute the code as per the terms.
