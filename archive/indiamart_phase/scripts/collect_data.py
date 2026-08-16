import requests
import time
from bs4 import BeautifulSoup
import json

urls = [
    "https://www.indiamart.com/proddetail/schneider-rxm4ab2jd-miniature-plug-in-relay-6-a-4-co-led-12-v-dc-2856326491362.html",
    "https://www.indiamart.com/proddetail/electrical-power-relays-2850397955073.html",
    "https://www.indiamart.com/proddetail/cgi14s-self-powered-relay-2852681175497.html",
    "https://www.indiamart.com/proddetail/hongfa-relay-hf3fa024-12st-2854371170848.html",
    "https://www.indiamart.com/proddetail/zelio-logic-smart-relay-2115430991.html",
    "https://www.indiamart.com/proddetail/trainity-power-factor-relay-23988680755.html",
    "https://www.indiamart.com/proddetail/ly2-dc24-omron-power-relay-16104835162.html",
    "https://www.indiamart.com/proddetail/miniature-industrial-relay-rm699-slim-relay-26179220591.html",
    "https://www.indiamart.com/proddetail/leone-industrial-relays-12181567562.html",
    "https://www.indiamart.com/proddetail/ev200haana-industrial-relays-2858281166433.html",
    "https://www.indiamart.com/proddetail/industrial-connector-han-2853882833897.html",
    "https://www.indiamart.com/proddetail/industrial-connectors-2854355990348.html",
    "https://www.indiamart.com/proddetail/elcom-industrial-connector-2853645129388.html",
    "https://www.indiamart.com/proddetail/10-pin-heavy-duty-connector-7184221473.html",
    "https://www.indiamart.com/proddetail/industrial-ethernet-connector-2851951730555.html",
    "https://www.indiamart.com/proddetail/elcom-6548-industrial-connector-2857428968033.html",
    "https://www.indiamart.com/proddetail/mennekes-3457-industrial-connector-21761321830.html",
    "https://www.indiamart.com/proddetail/industrial-connector-2857952287748.html",
    "https://www.indiamart.com/proddetail/ji-go-industrial-connector-2856884550197.html",
    "https://www.indiamart.com/proddetail/siemens-connector-smi20-2854715939133.html",
    "https://www.indiamart.com/proddetail/prince-c-curve-miniature-circuit-beaker-2859204411662.html",
    "https://www.indiamart.com/proddetail/mcb-single-pole-switch-13664171591.html",
    "https://www.indiamart.com/proddetail/miniature-circuit-breaker-4095888730.html",
    "https://www.indiamart.com/proddetail/miniature-circuit-breaker-mcb-2859041353388.html",
    "https://www.indiamart.com/proddetail/nb1-63h-miniature-circuit-breaker-b-curve-mcb-1p-to-4p-2854097974762.html",
    "https://www.indiamart.com/proddetail/mcb-30-miniature-circuit-breaker-2859277674955.html",
    "https://www.indiamart.com/proddetail/ac-mcb-4p-32amp-infi-brand-2854896198988.html",
    "https://www.indiamart.com/proddetail/schneider-mcb-switch-2853701467033.html",
    "https://www.indiamart.com/proddetail/3-pole-miniature-circuit-breaker-2856362822230.html",
    "https://www.indiamart.com/proddetail/electrical-mcb-22433025662.html",
    "https://www.indiamart.com/proddetail/door-gate-switches-23165255430.html",
    "https://www.indiamart.com/proddetail/industrial-switches-2855779657988.html",
    "https://www.indiamart.com/proddetail/heavy-duty-switches-for-tankers-3458197330.html",
    "https://www.indiamart.com/proddetail/industrial-switch-24217649973.html",
    "https://www.indiamart.com/proddetail/industrial-managed-switch-15464025612.html",
    "https://www.indiamart.com/proddetail/industrial-grade-switches-15838777297.html",
    "https://www.indiamart.com/proddetail/industrial-switch-24054856288.html",
    "https://www.indiamart.com/proddetail/electrical-switch-4893707412.html",
    "https://www.indiamart.com/proddetail/industrial-switches-04pi-2855464951088.html",
    "https://www.indiamart.com/proddetail/industrial-switch-9306118662.html",
    "https://www.indiamart.com/proddetail/salzer-industrial-plug-sockets-2854150142548.html",
    "https://www.indiamart.com/proddetail/industrial-plug-and-socket-2851598772812.html",
    "https://www.indiamart.com/proddetail/hcl-plug-socket-2858821137230.html",
    "https://www.indiamart.com/proddetail/plug-socket-combination-2855531567233.html",
    "https://www.indiamart.com/proddetail/industrial-plug-sockets-26494365148.html",
    "https://www.indiamart.com/proddetail/green-power-16-amp-3-pin-industrial-plug-and-sockets-23403137212.html",
    "https://www.indiamart.com/proddetail/industrial-plugs-socket-22417355288.html",
    "https://www.indiamart.com/proddetail/industrial-plug-and-socket-18602547333.html",
    "https://www.indiamart.com/proddetail/industrial-electrical-plug-socket-25904181191.html",
    "https://www.indiamart.com/proddetail/industrial-electrical-plug-2855437565873.html",
    "https://www.indiamart.com/proddetail/contactor-32-amp-2856562721230.html",
    "https://www.indiamart.com/proddetail/schneider-lc1d95-tesys-ac-control-2855699463312.html",
    "https://www.indiamart.com/proddetail/l-t-mo-c25-capacitor-duty-power-contactors-21747346391.html",
    "https://www.indiamart.com/proddetail/vastav-anand-2-pole-contactor-2855458533173.html",
    "https://www.indiamart.com/proddetail/2-pole-contractor-chinna-type-2853699662130.html",
    "https://www.indiamart.com/proddetail/industrial-dc-contactors-2854336028273.html",
    "https://www.indiamart.com/proddetail/industrial-dc-contactor-2858966489730.html",
    "https://www.indiamart.com/proddetail/industrial-ac-contactor-27128254548.html",
    "https://www.indiamart.com/proddetail/industrial-ac-contactor-2859272038155.html",
    "https://www.indiamart.com/proddetail/nc2-contactor-4p-ac-coil-2854090363873.html",
    "https://www.indiamart.com/proddetail/connector-18042595630.html",
    "https://www.indiamart.com/proddetail/se009-15a-terminal-block-3way-sq-2854150142191.html",
    "https://www.indiamart.com/proddetail/283-901-wago-terminal-block-2858089159873.html",
    "https://www.indiamart.com/proddetail/ftc-terminal-block-18509251233.html",
    "https://www.indiamart.com/proddetail/chint-jxb-series-and-sak-terminal-blocks-2854104845273.html",
    "https://www.indiamart.com/proddetail/100-amp-terminal-block-2858081267362.html",
    "https://www.indiamart.com/proddetail/power-terminal-block-2851781812097.html",
    "https://www.indiamart.com/proddetail/grey-pcb-terminal-blocks-26432707930.html",
    "https://www.indiamart.com/proddetail/autonics-afs-h40-terminal-2859095251130.html",
    "https://www.indiamart.com/proddetail/panel-mount-barrier-terminal-block-21102319355.html",
    "https://www.indiamart.com/proddetail/white-moulded-case-circuit-breaker-26864533491.html",
    "https://www.indiamart.com/proddetail/hager-mccb-63-amp-4-pole-18-ka-hda081z-2855197522462.html",
    "https://www.indiamart.com/proddetail/l-t-mccb-circuit-breaker-2859318322812.html",
    "https://www.indiamart.com/proddetail/l-t-mccb-circuit-breaker-2854350304997.html",
    "https://www.indiamart.com/proddetail/eaton-molded-case-circuit-breaker-2849295083891.html",
    "https://www.indiamart.com/proddetail/mccb-circuit-breaker-14787719588.html",
    "https://www.indiamart.com/proddetail/lnt-molded-case-circuit-breaker-11907186488.html",
    "https://www.indiamart.com/proddetail/d-sine-series-l-t-mccb-20752898133.html",
    "https://www.indiamart.com/proddetail/moulded-case-circuit-breaker-2856479787855.html",
    "https://www.indiamart.com/proddetail/dh-100-moulded-case-circuit-breakers-24334753633.html",
    "https://www.indiamart.com/proddetail/j-lock-cable-gland-2859185735633.html",
    "https://www.indiamart.com/proddetail/metal-cable-gland-2851781801173.html",
    "https://www.indiamart.com/proddetail/cable-gland-and-accessories-2854347452697.html",
    "https://www.indiamart.com/proddetail/brass-cable-gland-2854336028948.html",
    "https://www.indiamart.com/proddetail/brass-cable-glands-3846615891.html",
    "https://www.indiamart.com/proddetail/ul-approved-m25-cable-gland-2859600347830.html",
    "https://www.indiamart.com/proddetail/cable-glands-accessories-2852949781288.html",
    "https://www.indiamart.com/proddetail/m-series-cable-gland-26180420588.html",
    "https://www.indiamart.com/proddetail/brass-cable-gland-22592010291.html",
    "https://www.indiamart.com/proddetail/trinity-touch-cable-gland-21847338791.html",
    "https://www.indiamart.com/proddetail/electrical-junction-box-2858602788188.html",
    "https://www.indiamart.com/proddetail/electrical-junction-box-2856734412030.html",
    "https://www.indiamart.com/proddetail/electric-junction-box-powder-coated-20624186988.html",
    "https://www.indiamart.com/proddetail/junction-box-rmj-25565658097.html",
    "https://www.indiamart.com/proddetail/sheet-metal-junction-box-2851789018491.html",
    "https://www.indiamart.com/proddetail/polycarbonate-electrical-junction-box-1180980555.html",
    "https://www.indiamart.com/proddetail/120mmx120mm-electrical-junction-boxes-2858862186455.html",
    "https://www.indiamart.com/proddetail/junction-box-3001518755.html",
    "https://www.indiamart.com/proddetail/hensel-dk-0402-g-ip66-junction-box-2859641619697.html",
    "https://www.indiamart.com/proddetail/hensel-dk-0202-g-cable-junction-boxes-ip-66-grey-with-integrated-2858540233491.html",
]

def clean_product_name(raw_title):
    if raw_title == "Not found":
        return raw_title
    # " at " ke pehle wala hissa nikaalte hain (jaha price/location shuru hota hai)
    if " at " in raw_title:
        name = raw_title.split(" at ")[0]
    else:
        name = raw_title
    return name.strip()


def clean_manufacturer(raw_manufacturer):
    if raw_manufacturer == "Not found":
        return raw_manufacturer

    # Ye junk values hain jo asal manufacturer naam nahi hain,
    # seller ne galti se Brand field mein daal diya
    junk_values = ["no", "n/a", "na", "-", "none", "all", "yes", "standard", ""]

    if raw_manufacturer.strip().lower() in junk_values:
        return "Not found"

    return raw_manufacturer.strip()


def detect_category(url):
    # URL mein keywords dhundh ke category assign karte hain
    # Order matters: zyada specific keywords pehle check karte hain
    # taaki galat match na ho (e.g. "mccb" na "mcb" ban jaye)
    url_lower = url.lower()

    category_keywords = [
        ("MCCB", ["mccb", "molded-case-circuit-breaker", "moulded-case-circuit-breaker"]),
        ("MCB / Circuit Breaker", ["mcb", "circuit-beaker", "circuit-breaker"]),
        ("Relay", ["relay"]),
        ("Connector", ["connector"]),
        ("Switch", ["switch"]),
        ("Socket / Plug", ["socket", "plug"]),
        ("Contactor", ["contactor", "contractor"]),
        ("Terminal Block", ["terminal-block", "terminal"]),
        ("Cable Gland", ["cable-gland"]),
        ("Junction Box", ["junction-box"]),
    ]

    for category_name, keywords in category_keywords:
        for keyword in keywords:
            if keyword in url_lower:
                return category_name

    return "Not found"


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

all_products = []
failed_urls = []

for url in urls:
    response = None
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                break
            else:
                print(f"Attempt {attempt+1} failed (status {response.status_code}) for {url}")
                time.sleep(5)
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt+1} error: {e} for {url}")
            time.sleep(5)

    if response is None or response.status_code != 200:
        print(f"FAILED after 3 attempts: {url}")
        failed_urls.append(url)
        time.sleep(2)
        continue

    soup = BeautifulSoup(response.text, "html.parser")

    page_title = soup.title.string if soup.title else "Not found"
    product_name = clean_product_name(page_title)
    category = detect_category(url)

    price_element = soup.find(id="askprice_pg-1")
    price = price_element.get_text(strip=True) if price_element else "Not found"

    seller_element = soup.find("p", class_="fs16 bo7")
    seller = seller_element.get_text(strip=True) if seller_element else "Not found"

    specs = {}
    label_cells = soup.find_all("td", class_="tdwdt")
    for label_cell in label_cells:
        label = label_cell.get_text(strip=True)
        value_cell = label_cell.find_next_sibling("td")
        if value_cell:
            value = value_cell.get_text(strip=True)
            specs[label] = value

    # Manufacturer ko specs mein se dhundte hain - alag alag naam se aa sakta hai
    manufacturer = "Not found"
    for possible_key in ["Brand", "Product Brand", "Manufacturer", "Make"]:
        if possible_key in specs:
            manufacturer = specs[possible_key]
            break
    manufacturer = clean_manufacturer(manufacturer)

    product = {
        "product_name": product_name,
        "category": category,
        "price_range": price,
        "manufacturer": manufacturer,
        "seller_name": seller,
        "specifications": specs,
        "source_type": "website_html",
        "source_url": url
    }

    all_products.append(product)
    print("Processed:", page_title[:50], "...")
    print("Manufacturer:", manufacturer, "| Seller:", seller)
    time.sleep(2)

with open("raw_data/html/products.json", "w", encoding="utf-8") as f:
    json.dump(all_products, f, indent=2, ensure_ascii=False)

print("\nSaved", len(all_products), "products to raw_data/html/products.json")
print("Total failed after retries:", len(failed_urls))
if failed_urls:
    print("Failed URLs:")
    for u in failed_urls:
        print(" -", u)