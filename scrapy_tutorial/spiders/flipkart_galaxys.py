# Name:                 Ritvik Gupta
# Registration Number:  19BCE0397

import re

import scrapy

PHONE_COLOR_FILTER = "(PRODUCT)"
# Colors would additionally have such redundant info
# which needs to be filtered

PHONE_GENERAL_SPECS_FILTER_GROUP = {
    "In The Box",
    "SIM Type",
    "Hybrid Sim Slot",
    "Touchscreen",
    "OTG Compatible",
    "Additional Content",
}  # Only fetched the relevant Specs from the General Category in the Set


class FlipkartGalaxysSpider(scrapy.Spider):
    # Unique Name for the Spider
    name = "flipkart_galaxys"

    allowed_domains = ["flipkart.com"]
    start_urls = [
        "https://www.flipkart.com/mobiles/pr?sid=tyy%2C4io&p%5B%5D=facets.brand%255B%255D%3DSAMSUNG&otracker=clp_metro_expandable_7_3.metroExpandable.METRO_EXPANDABLE_Shop%2BNow_mobile-phones-store_Q0QIS4SPJNLH_wp3&fm=neo%2Fmerchandising&iid=M_346e3244-39f0-41e5-9bba-b53bf061418f_3.Q0QIS4SPJNLH&ppt=hp&ppn=homepage&ssid=64a7ventkg0000001645414617403&page=1"
    ]  # First Page URL

    # Parses each individual Samsung Phone
    # and yields ( generates ) a list/dictionary of its components
    def parse_galaxy(self, response, image_url, phone_url):

        # Context Functions to fetch one field which requires parsing
        def extract_total_reviews():
            reviews_str = response.css("span._13vcmD + span::text").get().strip()
            # As the Reviews fetched contains redundant "Reviews" string
            # remove it and convert to integer
            return int(reviews_str[: reviews_str.index(" Reviews")].replace(",", ""))

        def extract_price():
            price = 0

            price_str = response.css("div._30jeq3._16Jk6d::text").get()
            # The Price is of format "$ XXXX" and we only are interested in
            # the actual amount in integer. Also UNICODE '$' is hard to parse in CSV
            match_first_digit = re.search(r"\d", price_str)
            if match_first_digit:  # Match for the first Digit found
                # And parse to get only the integer part
                price = int(price_str[match_first_digit.start() :].replace(",", ""))
            return price

        galaxy_details = {
            "Image URL": image_url,  # Context Arguments passed from
            "Phone URL": phone_url,  # Parent caller
            "Name": response.css("h1 span.B_NuCI::text").get(default="galaxy").strip(),
            "Rating": float(response.css("div._3LWZlK::text").get().strip()),
            "Total Reviews": extract_total_reviews(),
            "Price": extract_price(),
            "Colors": [
                color.replace(PHONE_COLOR_FILTER, "").capitalize()
                for color in response.css(
                    "span#Color + ul li._3V2wfe div div::text"
                ).getall()
            ],  # Mined colors would be a list of names but parsing is needed
            "Storages": response.css("span#Storage + ul li._3V2wfe a::text").getall(),
        }

        # As there are multiple tables for different Specifications
        # We first find the General Specs table ( using Regex pattern matching )
        # and the resultant HTML string is converted back to a Selector element
        general_specs_table_selector = scrapy.Selector(
            text=response.css("div._1UhVsV div").re(r".*General.*")[0]
        )  # Select and Parse the General Specs table

        general_specs = {}  # Create a Nesting in the JSON structure for General Specs
        for row in general_specs_table_selector.css("table tbody tr"):
            # For every Table Row, the rows have 2 columns each

            # First Column contains the Key Name
            key = row.css("td:nth-child(1)::text").get()
            if key not in PHONE_GENERAL_SPECS_FILTER_GROUP:
                continue

            # Second Column would have the Value for the particular phone
            general_specs[key] = row.css("td:nth-child(2) ul li::text").get()

        galaxy_details[
            "General Specs"
        ] = general_specs  # Store the Nested General Specs
        yield galaxy_details

    def parse(self, response):
        for galaxy in response.css("a._1fQZEK"):  # For every Phone on the Main Page
            # Galaxy Phone would be an anchor tag that can be followed
            # to get further details about this phone
            yield response.follow(
                galaxy,
                callback=self.parse_galaxy,
                cb_kwargs={
                    "image_url": galaxy.css("img._396cs4._3exPp9::attr(src)").get(),
                    "phone_url": response.urljoin(galaxy.css("::attr(href)").get()),
                },
                # Pass in additional Arguments as the Child Process
                # for the particular phone would not have these attributes
            )
