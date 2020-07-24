import csv
import datetime
import time
from pprint import pprint

import requests
import dateutil.parser

USERNAME = "email go here"
PASSWORD = "password go here"

class GOATAPI:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.token = None
        self.user = None

        self.S = requests.Session()
        self.headers = {
            "x-px-authorization": "3:fb4649ab0a921fd8cb1ab218498d2afe27caff5ed5489c01731b4b40135e225f:Zl97rEeCqfMwevJh+XBo03freLHzC58sQ9WPvJ1FTeCiLRXCFaOLRAPD9R1PCDTCUTYldfHvuhZQIjDC80k5Eg==:1000:Yt/VlMbAhYt7MqkeIAt3v/O96Vzm9RhRiqlyTdaJfAt9ibpmUAUNaiopCL7aWYW3xGeKDOing4xFO877qhJdjCCMZpxT34LekcaDNRVThUUieDYDj/bDpPyPIzQk4w/GvwpJnhw4kVlwgTWAGh7f6eb0QCXBo2eVj9s9QuMe4Lo=",
            'accept':'application/json',
            'authorization':'Token token=""',
            'accept-language':'en-au',
            'accept-encoding':'gzip, deflate, br',
            'x-emb-st':'1592042226393',
            'user-agent':'GOAT/2.29.0 (iPhone; iOS 13.5; Scale/3.00) Locale/en',
            'x-emb-id':'E06F3FEF6F33431EB193BBF3E5F0A819',
        }

        self.orders = None

    def update_headers(self):
        self.headers['x-emb-st'] = str(int(time.time() * 1000))
        self.headers['authorization'] = 'Token token="{0}"'.format(self.token if self.token is not None else "")

    def login(self):
        print("Logging in")
        login_data = {
            "user[login]": self.username,
            "user[password]": self.password
        }
        self.update_headers()
        resp = self.S.post("https://www.goat.com/api/v1/users/sign_in", data=login_data, headers=self.headers)
        if resp.status_code == 200:
            self.user = resp.json()
            self.token = resp.json()['authToken']
        else:
            raise Exception("Bad response received from login api: %s" % resp.text)

    def get_all_sales(self):
        def get_sales_page(page):
            print("Getting sales page: %s" % page)
            self.update_headers()
            return self.S.get("https://www.goat.com/api/v1/orders?filter=sell&page=%s" % page, headers=self.headers)

        def extract_sales_from_page(page_data):
            orders = page_data['orders']
            return orders
        
        first_page = get_sales_page("1").json()
        total_results = first_page['metadata']['totalCount']
        pages = first_page['metadata']['totalPages']
        print("Total sales found: %s; Total pages: %s" % (total_results, pages))

        orders = extract_sales_from_page(first_page)
        if pages > 1:
            for page in range(2, pages+1):
                next_page = get_sales_page(str(page)).json()
                new_orders = extract_sales_from_page(next_page)
                orders += new_orders
        
        self.orders = orders
        

    def export_all_orders(self):
        while self.token is None:
            self.login()
        
        self.get_all_sales()
        pprint(self.orders)

    def write_orders_to_csv(self):
        orders_written = []
        with open("invoices.csv", "w") as template:
            fieldnames = ['*ContactName', 'EmailAddress', 'POAddressLine1', 'POAddressLine2', 'POAddressLine3', 'POAddressLine4', 'POCity', 'PORegion', 'POPostalCode', 'POCountry', '*InvoiceNumber', 'Reference', '*InvoiceDate', '*DueDate', 'Total', 'InventoryItemCode', '*Description', '*Quantity', '*UnitAmount', 'Discount', '*AccountCode', '*TaxType', 'TaxAmount', 'TrackingName1', 'TrackingOption1', 'TrackingName2', 'TrackingOption2', 'Currency', 'BrandingTheme']
            out = csv.DictWriter(template, fieldnames)
            out.writeheader()
            for order in self.orders:
                if order['status'] in ['canceled_by_seller', 'canceled_by_buyer', 'fraudulent', 'goat_issue_resolved', 'goat_received', 'seller_confirmed']:
                    # skip incomplete sales
                    continue
                meta = {
                    "*ContactName": "GOAT",
                    "*InvoiceNumber": "GOAT-" + str(order['number']), #+ "-1",
                    "Reference": order['number'],
                    "*InvoiceDate": str(dateutil.parser.parse(order['purchasedAt']).date()),
                    "*DueDate": str(datetime.date.today()),
                    "Total": str(order['sellerAmountMadeCents'] / 100),
                    "Currency": "USD"
                }
                line_item = {
                    "*Description": "Sale #{0} of {1} - SKU: {2}".format(
                        order['number'],
                        order['product']['productTemplate']['name'],
                        order['product']['productTemplate']['sku'],
                    ),
                    "*Quantity": "1",
                    "*UnitAmount": str(order['product']['priceCents'] / 100),
                    "*AccountCode": "200",
                    "*TaxType": "Zero Rated Income"
                }
                fee = {
                    "*Description": "GOAT Fee",
                    "*Quantity": "1",
                    "*UnitAmount": "-" + str((int(order['product']['priceCents']) - int(order['sellerAmountMadeCents']))/100),
                    "*AccountCode": "310",
                    "*TaxType": "No VAT",
                }
                fee = {**fee, **meta}
                line_item = {**line_item, **meta}
                out.writerow(line_item)
                out.writerow(fee)
                orders_written.append(order['number'])
        print("-----Orders exported-----")
        for order_number in orders_written:
            print(order_number)
        

if __name__ == "__main__":
    api = GOATAPI(USERNAME, PASSWORD)
    api.export_all_orders()
    api.write_orders_to_csv()