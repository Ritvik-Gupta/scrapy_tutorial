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


class FlipkartIphonesSpider(scrapy.Spider):
    # Unique Name for the Spider
    name = "flipkart_iphones"

    allowed_domains = ["flipkart.com"]
    start_urls = [
        "https://www.flipkart.com/mobiles/pr?sid=tyy%2C4io&p%5B%5D=facets.brand%255B%255D%3DApple&otracker=clp_metro_expandable_6_3.metroExpandable.METRO_EXPANDABLE_Shop%2BNow_mobile-phones-store_92RED14GXPXF_wp3&fm=neo%2Fmerchandising&iid=M_601c4f2d-8f76-4c55-a92d-ad96ecdded4d_3.92RED14GXPXF&ppt=browse&ppn=browse&ssid=665qlfhk1s0000001645344877842&page=1"
    ]  # First Page URL

    # Parses each individual iPhone
    # and yields ( generates ) a list/dictionary of its components
    def parse_iphone(self, response, image_url, phone_url):

        # Context Functions to fetch one field which requires parsing
        def extract_total_reviews():
            reviews_str = (
                response.css("span._13vcmD + span::text").get(default="0").strip()
            )
            # As the Reviews fetched contains redundant "Reviews" string
            # remove it and convert to integer
            return int(reviews_str[: reviews_str.index(" Reviews")].replace(",", ""))

        def extract_price():
            price = 0

            price_str = response.css("div._30jeq3._16Jk6d::text").get(default="0")
            # The Price is of format "$ XXXX" and we only are interested in
            # the actual amount in integer. Also UNICODE '$' is hard to parse in CSV
            match_first_digit = re.search(r"\d", price_str)
            if match_first_digit:  # Match for the first Digit found
                # And parse to get only the integer part
                price = int(price_str[match_first_digit.start() :].replace(",", ""))
            return price

        # As this is scraped into a CSV file it wont support Nested structures
        # like JSON and Arrays are converted to strings for proper notation
        iphone_details = {
            "Image URL": image_url,  # Context Arguments passed from
            "Phone URL": phone_url,  # Parent caller
            "Name": response.css("h1 span.B_NuCI::text").get(default="iPhone").strip(),
            "Rating": float(response.css("div._3LWZlK::text").get(default="0").strip()),
            "Total Reviews": extract_total_reviews(),
            "Price": extract_price(),
            "Colors": str(
                [
                    color.replace(PHONE_COLOR_FILTER, "").capitalize()
                    for color in response.css(
                        "span#Color + ul li._3V2wfe div div::text"
                    ).getall()
                ],
            ),  # Mined colors would be a list of names but parsing is needed
            "Storages": str(
                response.css("span#Storage + ul li._3V2wfe a::text").getall()
            ),
        }

        # As there are multiple tables for different Specifications
        # We first find the General Specs table ( using Regex pattern matching )
        # and the resultant HTML string is converted back to a Selector element
        general_specs_table_selector = scrapy.Selector(
            text=response.css("div._1UhVsV div").re(r".*General.*")[0]
        )  # Select and Parse the General Specs table

        for row in general_specs_table_selector.css("table tbody tr"):
            # For every Table Row, the rows have 2 columns each

            # First Column contains the Key Name
            key = row.css("td:nth-child(1)::text").get()
            if key not in PHONE_GENERAL_SPECS_FILTER_GROUP:
                continue

            # Second Column would have the Value for the particular phone
            value = row.css("td:nth-child(2) ul li::text").get()
            match value:  # In CSV we can store UNICODE Check and Cross Marks
                case "Yes":
                    value = "\u2705"
                case "No":
                    value = "\u274C"

            # Directly add the Specifications in the attributes
            # list as CSV dosen't support nested structure
            iphone_details[key] = value

        yield iphone_details

    def parse(self, response):
        for iphone in response.css("a._1fQZEK"):  # For every Phone on the Main Page
            # iPhone would be an anchor tag that can be followed
            # to get further details about this phone
            yield response.follow(
                iphone,
                callback=self.parse_iphone,
                cb_kwargs={
                    "image_url": iphone.css("img._396cs4._3exPp9::attr(src)").get(),
                    "phone_url": response.urljoin(iphone.css("::attr(href)").get()),
                },
                # Pass in additional Arguments as the Child Process
                # for the particular phone would not have these attributes
            )

        # Next, go to the "Next" Page if found any, thusrecursively visiting all pages
        yield from response.follow_all(response.css("._1LKTO3"), callback=self.parse)
        # Note: This Selector would also select the "Previous" Pages but
        # Scrapy Caches Requests and the same request would not be made again
