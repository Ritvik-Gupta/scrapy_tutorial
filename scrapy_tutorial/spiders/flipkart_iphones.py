# Name:                 Ritvik Gupta
# Registration Number:  19BCE0397

import re

import scrapy

PHONE_COLOR_FILTER = "(PRODUCT)"

PHONE_GENERAL_SPECS_FILTER_GROUP = {
    "In The Box",
    "SIM Type",
    "Hybrid Sim Slot",
    "Touchscreen",
    "OTG Compatible",
    "Additional Content",
}


class FlipkartIphonesSpider(scrapy.Spider):
    name = "flipkart_iphones"
    allowed_domains = ["flipkart.com"]
    start_urls = [
        "https://www.flipkart.com/mobiles/pr?sid=tyy%2C4io&p%5B%5D=facets.brand%255B%255D%3DApple&otracker=clp_metro_expandable_6_3.metroExpandable.METRO_EXPANDABLE_Shop%2BNow_mobile-phones-store_92RED14GXPXF_wp3&fm=neo%2Fmerchandising&iid=M_601c4f2d-8f76-4c55-a92d-ad96ecdded4d_3.92RED14GXPXF&ppt=browse&ppn=browse&ssid=665qlfhk1s0000001645344877842&page=1"
    ]

    def parse_iphone(self, response, image_url, phone_url):
        def extract_total_reviews():
            reviews_str = response.css("span._13vcmD + span::text").get().strip()
            return int(reviews_str[: reviews_str.index(" Reviews")].replace(",", ""))

        def extract_price():
            price = 0

            price_str = response.css("div._30jeq3._16Jk6d::text").get()
            match = re.search(r"\d", price_str)
            if match:
                price = int(price_str[match.start() :].replace(",", ""))
            return price

        iphone_details = {
            "Image URL": image_url,
            "Phone URL": phone_url,
            "Name": response.css("h1 span.B_NuCI::text").get(default="iPhone").strip(),
            "Rating": float(response.css("div._3LWZlK::text").get().strip()),
            "Total Reviews": extract_total_reviews(),
            "Price": extract_price(),
            "Colors": str(
                [
                    color.replace(PHONE_COLOR_FILTER, "").capitalize()
                    for color in response.css(
                        "span#Color + ul li._3V2wfe div div::text"
                    ).getall()
                ],
            ),
            "Storages": str(
                response.css("span#Storage + ul li._3V2wfe a::text").getall()
            ),
        }

        general_specs_table_selector = scrapy.Selector(
            text=response.css("div._1UhVsV div").re(r".*General.*")[0]
        )

        for row in general_specs_table_selector.css("table tbody tr"):
            key = row.css("td:nth-child(1)::text").get()
            if key not in PHONE_GENERAL_SPECS_FILTER_GROUP:
                continue

            value = row.css("td:nth-child(2) ul li::text").get()
            match value:
                case "Yes":
                    value = "\u2705"
                case "No":
                    value = "\u274C"
            iphone_details[key] = value

        yield iphone_details

    def parse(self, response):
        for iphone in response.css("a._1fQZEK"):
            yield response.follow(
                iphone,
                callback=self.parse_iphone,
                cb_kwargs={
                    "image_url": iphone.css("img._396cs4._3exPp9::attr(src)").get(),
                    "phone_url": response.urljoin(iphone.css("::attr(href)").get()),
                },
            )

        yield from response.follow_all(response.css("._1LKTO3"), callback=self.parse)
