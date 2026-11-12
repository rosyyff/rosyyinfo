import os
import time
import binascii
import logging
import threading
from datetime import datetime
import itertools

try:
    from zoneinfo import ZoneInfo
    TIMEZONE_AVAILABLE = True
except ImportError:
    TIMEZONE_AVAILABLE = False

import requests
from flask import Flask, jsonify, request
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from data_pb2 import AccountPersonalShowInfo
import uid_generator_pb2


# ============================================================
# Flask
# ============================================================

app = Flask(__name__)
app.json.sort_keys = False


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# Configuration
# ============================================================

RELEASE_VERSION = "OB55"

USER_AGENT = (
    "Dalvik/2.1.0 (Linux; U; Android 9; "
    "ASUS_Z01QD Build/PI)"
)

DEFAULT_KEY = "Yg&tc%DEuh6%Zc^8"
DEFAULT_IV = "6oyZDr22E3ychjM%"

IND_JWT_URL = (
    "https://kawsarxjwt.lovable.app/api/public/token"
)


# ============================================================
# Multi-Server Credentials Pools (112 IND Accounts + Othars)
# ============================================================

REGION_ACCOUNTS = {
    "IND": [
        {"uid": "8438227726", "password": "Mimii3DB4LL77QJUP49TQHFHJ3RSUQW"},
        {"uid": "8438227817", "password": "Mimii1IDJUKWFH4Y3A1RBZLWETPWD0C"},
        {"uid": "8438227913", "password": "MimiiM79UF1L90WPSPV440P387U2Q2T"},
        {"uid": "8438228212", "password": "MimiiHUCE1JLHLMRXEACQVIZYJUELPA"},
        {"uid": "8438228037", "password": "Mimii7ZHYEAAKMAUKEOR02MFA9FF3HR"},
        {"uid": "8438227574", "password": "MimiiQK1R3GZSZ9YX2XILMYE2I7V0GM"},
        {"uid": "8438228391", "password": "MimiiYP8138G49CV46U97U8JH9V5BMG"},
        {"uid": "8438234762", "password": "MimiiIO46PINKIOBDGFNVR1978DMBGG"},
        {"uid": "8438234680", "password": "MimiiX6A046O9VBO01UAEOMGPQ4M07J"},
        {"uid": "8438234805", "password": "MimiiRKKJBAG8Q11FTC0R7KYR8GA8G1"},
        {"uid": "8438234924", "password": "MimiiNDLZEID8MZ5P3TO3HNGQA6ELRN"},
        {"uid": "8438234866", "password": "MimiiX09ZS7301WCS63MXXIQGJU7DBQ"},
        {"uid": "8438234975", "password": "MimiiXIMKKOTDZFH4UQNC5ABAGISNZR"},
        {"uid": "8438234859", "password": "Mimii0I6HDJUXWSXDU2K8PDLPUCX1YG"},
        {"uid": "8438235001", "password": "MimiiA34LVA246ZO8MHAQT8PMU5KOL2"},
        {"uid": "8438234930", "password": "MimiiNV1G1DBZHRFXRLRSMYDNSJ858E"},
        {"uid": "8438235050", "password": "Mimii2VNSCBMVTQEFJFBYZ5C7A7PZJZ"},
        {"uid": "8438241545", "password": "MimiiRWAD7OQA5SJKO057FPYL519FHZ"},
        {"uid": "8438241561", "password": "MimiiZNUBNLB2KH5UG2GHUJTXWK74XC"},
        {"uid": "8438241666", "password": "MimiiICFNSTX3NPDFT2JECEWNECZMSG"},
        {"uid": "8438241702", "password": "MimiiZPKYH7C6IUAIET4DBNEQUDYVRI"},
        {"uid": "8438241739", "password": "Mimii8LU1Q2ZSSS9HCLCJA2LOQHQNMY"},
        {"uid": "8438241728", "password": "MimiiMZJ5G6H29GQEOOO6RUCOM2O7EN"},
        {"uid": "8438241703", "password": "MimiiS1Q43DZDH4RY1T1C3ZG3PU5GYF"},
        {"uid": "8438241731", "password": "MimiiZJ4T5DTLVNOWWGN46ETMMYAST4"},
        {"uid": "8438249454", "password": "MimiiET3WP48P4UCTX2GJK11XDFQMG7"},
        {"uid": "8438249417", "password": "MimiiR0JM2D2I2RMAW4R69E4A89WYVE"},
        {"uid": "8438249490", "password": "MimiiTSBZD8YPE034D6LL9W3ZOKO9V5"},
        {"uid": "8438249481", "password": "MimiiFSYTK9DQB3I03IL1YBKJ1KPDQ1"},
        {"uid": "8438249342", "password": "MimiiPZ4S3WE677LNM0TN6NCB4A3QRV"},
        {"uid": "8438254267", "password": "MimiiFT1S5QB0C0TDW430PT7EESKH6O"},
        {"uid": "8438254132", "password": "MimiiDUGIUJ87F5CXBKNC2G9L8G0M9J"},
        {"uid": "8438254291", "password": "MimiiVHPQDK2JXMPZDGJXUYUETSK3NL"},
        {"uid": "8438254365", "password": "MimiiLX8S8TO73RA22C9NHQKS34ZFNL"},
        {"uid": "8438254407", "password": "MimiiXSKO3IB80KY0FX25FEJSG4EU8S"},
        {"uid": "8438254450", "password": "MimiiJF56GDZ96PEKLU1N917CYYIPZY"},
        {"uid": "8438254364", "password": "MimiiP51I6PJ4SMWMMTVB092EQZAU2J"},
        {"uid": "8438254419", "password": "MimiiLTRYF1E982NJ8EQ0ULOM6O98GG"},
        {"uid": "8438262148", "password": "MimiiLRVPNNHMHEGQL8XFH29G9H2LHP"},
        {"uid": "8438262021", "password": "MimiiWJQFA4LX3Q6GO0RAJKH9ACD2BR"},
        {"uid": "8438262325", "password": "MimiiU2TWDM07E9NYLKY4TCB0XG27BN"},
        {"uid": "8438262206", "password": "MimiiQXTXCDMQ7GA1F005GBO3FV0K4F"},
        {"uid": "8438261998", "password": "MimiiCHF59ESHP59RFBC8C5UB9BS73D"},
        {"uid": "8438262337", "password": "Mimii46DEHEQ82DM1I9STVV5DB3YCEI"},
        {"uid": "8438262364", "password": "Mimii75ELD6HSBA26XPLP00P5YYOEAU"},
        {"uid": "8438298563", "password": "Mimii2I652FFO2TD10VKY8OT4V0FYPZ"},
        {"uid": "8438298548", "password": "Mimii0JNJJUDV6SPYH67YUJTS1OPT2N"},
        {"uid": "8438298552", "password": "MimiiXZJ7WTWT2UD2D5ADEWXE9KLXI4"},
        {"uid": "8438298561", "password": "Mimii1GE53POYHWD8D7EZQUTP82TWQ9"},
        {"uid": "8438298550", "password": "Mimii9A8K5YMR215672FEZDWEMI42TX"},
        {"uid": "8438298564", "password": "MimiiWH5CFU81TINRJ6LE0A2UR3VX4B"},
        {"uid": "8438298557", "password": "MimiiD6LIUG296HD2QX3UCN6TCPW7N9"},
        {"uid": "8438298562", "password": "MimiiQUC1V0K8CKR6NHAURVC0W5PV7E"},
        {"uid": "8438298560", "password": "MimiiIKGOEZCSRBAJE6K1VET6BSZF7N"},
        {"uid": "8438300981", "password": "Mimii7FB8CU8ELQXKNSHV2XRKA5AEO2"},
        {"uid": "8438300832", "password": "MimiiXJFX4GFK4ECR01NKK91YOG0AGW"},
        {"uid": "8438303434", "password": "MimiiS0TW7GEQW8I6G1B6X7VMOIBSQ5"},
        {"uid": "8438303424", "password": "MimiiH5MWO8DZE7SLS75AV23OQ3AVLO"},
        {"uid": "8438303437", "password": "MimiiVOW9U1M5MTN82VGFBWW8WM4MW4"},
        {"uid": "8438303465", "password": "Mimii1VPQC4H5VD2YDOT9H9S1CCPSRP"},
        {"uid": "8438303472", "password": "MimiiWORRMZXJPD6NL49PB2B97CF8P6"},
        {"uid": "8438303446", "password": "Mimii458XA13TSGJ3IGSWF4KRHCXXVI"},
        {"uid": "8438304485", "password": "MimiiX83V8ODMP61WEYJ1Q5WY3O6UCV"},
        {"uid": "8438304489", "password": "MimiiEEWL1SAO6NVH7VJ7Y7NPRGZYCH"},
        {"uid": "8438304486", "password": "MimiiSJFOG19809M0XZ5GGGPE9IZZP7"},
        {"uid": "8438304490", "password": "MimiiCB72XG519R0MYVIGU3IWU1BSOS"},
        {"uid": "8438304492", "password": "MimiiFAU9298N3WG4AQJZXGF3M6L9CV"},
        {"uid": "8438304488", "password": "Mimii2BQ4IPVJ1AS9YP7QKRF6ICRK7B"},
        {"uid": "8438304487", "password": "MimiiHHKGIFOZJYJ1LTQ75ZWGW17LFH"},
        {"uid": "8438305533", "password": "MimiiHS8BC4E619CE4W8AJ1LOQQ870B"},
        {"uid": "8438305560", "password": "MimiiGEHXKQEVFA31S52MGHPZT1RVT3"},
        {"uid": "8438305557", "password": "Mimii6DDOIL1YAZ5DUWX9G6F20UBCZJ"},
        {"uid": "8438305551", "password": "MimiiZLQYHVE6NOBKORHZQ0S0TKU7QQ"},
        {"uid": "8438305599", "password": "Mimii35YPSYAXEQU0QYQTWH2WZDXS5T"},
        {"uid": "8438305604", "password": "Mimii2TA9YPLLMOW57S14DRGZ2868CA"},
        {"uid": "8438305575", "password": "Mimii13UPGHEYS74HKWQCIVFPRHEB1N"},
        {"uid": "8438308070", "password": "MimiiUBVZTHJROR5E3GXOI4OTBK2POJ"},
        {"uid": "8438308066", "password": "MimiiG3NF84THVR5TZCUOHRND46DG0C"},
        {"uid": "8438308072", "password": "MimiiB54E07KSHQR3D7KCID0RNNEFHV"},
        {"uid": "8438308073", "password": "Mimii3DAHGTIIXX146LWKCB8ZAB5EZ7"},
        {"uid": "8438308068", "password": "MimiiIQGBUMZ8PPWCJNUMM46JYWBE0W"},
        {"uid": "8438308069", "password": "Mimii8Z55YNC7WPOO5LMDZFV6SXHC4N"},
        {"uid": "8438308067", "password": "MimiiU8FHA11M9ROGJ8SPHPZ7RP4MCM"},
        {"uid": "8438308071", "password": "MimiiHK54YX2H6US15BYWB828NBUH64"},
        {"uid": "8438308064", "password": "MimiiII4HTYB9UEF86S6TKL0RRP4FP0"},
        {"uid": "8438316985", "password": "Mimii55I6NEHDO3ILMS3GPL8HQABPB3"},
        {"uid": "8438317099", "password": "MimiiD0UD56W9WWPBZY5B4BYP6C4YY5"},
        {"uid": "8438317184", "password": "MimiiMKHRVQ3HN09K37ADDQLFGR56CA"},
        {"uid": "8438317172", "password": "Mimii4HCSWQ5GO70ZS7EY0G61TD265Q"},
        {"uid": "8438317181", "password": "MimiiRIRKFOWO2AIHYCMSZCURDZYXCX"},
        {"uid": "8438317238", "password": "MimiiD1D5RXBC6FIINSW6UVX0ZCH9G4"},
        {"uid": "8438317229", "password": "MimiiSBFPZK5QENAY3E2OK5DEFMZVD8"},
        {"uid": "8438317110", "password": "MimiiQM39KT9718F1NXAX371OXNCUSF"},
        {"uid": "8438317270", "password": "MimiiE29RYJJQC8OEAYNACDLRG0TKOX"},
        {"uid": "8438317498", "password": "MimiiNDVAZEHGWJSD3FKSROALD3YA25"},
        {"uid": "8438321107", "password": "Mimii10YA60JX7N8A8CP8E2M976O97Q"},
        {"uid": "8438321168", "password": "MimiiKPF7K78ZY26KYLDCEMOB30WGCV"},
        {"uid": "8438321158", "password": "MimiiC8EG3GPTTV8ZCLKTSUETHFBBX6"},
        {"uid": "8438321312", "password": "MimiiS6LBC2VTS86GIT3UP2IMN7TIB4"},
        {"uid": "8438321276", "password": "MimiiSGVNKLJO2D10TG60LVHVTRORSP"},
        {"uid": "8438321197", "password": "MimiiB0X6ZGUL0KGQO6I1YUYGVLRU9X"},
        {"uid": "8438321232", "password": "Mimii6LL99LAF3K6FE25G654LR8R65M"},
        {"uid": "8438321198", "password": "MimiiHIAPBL86BY7301HUYFTOV0A4FC"},
        {"uid": "8438321205", "password": "MimiiX89IVMYBQ7XF3WS1ZYEB0ZUNCR"},
        {"uid": "8438321296", "password": "Mimii92LL7CYI39LC1Z6QL5K2P8MXFX"},
        {"uid": "8438323772", "password": "Mimii9RIKEZ276GDELIRZUDRNG0UV68"},
        {"uid": "8438323922", "password": "MimiiGM46KNR5JUN4U4I0F7F5PFW5R4"},
        {"uid": "8438323919", "password": "Mimii1MERC9BA3KT71MWT01V0SKYQE8"},
        {"uid": "8438323869", "password": "MimiiO2WCUZO6J9CKDK4XL4RMB77TMP"},
        {"uid": "8438323938", "password": "MimiiLCWCXO1AWL98372ZBAPFB6W1GK"},
        {"uid": "8438323956", "password": "MimiiR8R0RQ0FSI548SKKT1A9C1L9UU"},
        {"uid": "8438323973", "password": "Mimii55S2KTEUXMBZDMMYZI33FOJEQJ"},
    ],
    "OTHARS_SVR": [
        {
            "uid": os.getenv("OTHARS_UID_1", "7873585362"),
            "password": os.getenv("OTHARS_PASS_1", "XEROX_MODS_hmZovffkRNx8"),
        },
        {
            "uid": os.getenv("OTHARS_UID_2", "7873590047"),
            "password": os.getenv("OTHARS_PASS_2", "XEROX_MODS_f6IDOlrrT6is"),
        },
        {
            "uid": os.getenv("OTHARS_UID_3", "7873590071"),
            "password": os.getenv("OTHARS_PASS_3", "XEROX_MODS_ylPrinlBmvCt"),
        },
        {
            "uid": os.getenv("OTHARS_UID_4", "7873603877"),
            "password": os.getenv("OTHARS_PASS_4", "XEROX_MODS_YOTSbzFhJbSC"),
        },
        {
            "uid": os.getenv("OTHARS_UID_5", "7873608364"),
            "password": os.getenv("OTHARS_PASS_5", "XEROX_MODS_JkVZj6pph3oY"),
        },
    ],
}

region_cycles = {
    region: itertools.cycle(accounts)
    for region, accounts in REGION_ACCOUNTS.items()
}
cycle_locks = {region: threading.Lock() for region in REGION_ACCOUNTS}


# ============================================================
# JWT cache & locks
# ============================================================

jwt_tokens = {}
jwt_expiry = {}
jwt_lock = threading.Lock()
JWT_CACHE_SECONDS = 600


# ============================================================
# HTTP session with optimized pooling
# ============================================================

def create_http_session():
    session = requests.Session()
    retry = Retry(
        total=2,
        backoff_factor=0.2,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(
        max_retries=retry,
        pool_connections=50,
        pool_maxsize=50
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


http_session = create_http_session()


# ============================================================
# Safe Time Helper
# ============================================================

def get_formatted_time():
    if TIMEZONE_AVAILABLE:
        try:
            return datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%I:%M %p, %A, %B %d, %Y")
        except Exception:
            pass
    return datetime.now().strftime("%I:%M %p, %A, %B %d, %Y")


def get_iso_time():
    if TIMEZONE_AVAILABLE:
        try:
            return datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
        except Exception:
            pass
    return datetime.now().isoformat()
    # ============================================================
# Protobuf -> dict
# ============================================================

def proto_to_dict(message):
    result = {}
    for field in getattr(message.DESCRIPTOR, "fields", []):
        value = getattr(message, field.name)
        val_type = type(value).__name__

        if "MapContainer" in val_type:
            map_result = {}
            for key, item in value.items():
                if hasattr(item, "DESCRIPTOR"):
                    map_result[key] = proto_to_dict(item)
                elif isinstance(item, bytes):
                    map_result[key] = binascii.hexlify(item).decode("utf-8")
                else:
                    map_result[key] = item
            result[field.name] = map_result

        elif "Repeated" in val_type:
            list_result = []
            for item in value:
                if hasattr(item, "DESCRIPTOR"):
                    list_result.append(proto_to_dict(item))
                elif isinstance(item, bytes):
                    list_result.append(binascii.hexlify(item).decode("utf-8"))
                else:
                    list_result.append(item)
            result[field.name] = list_result

        elif hasattr(value, "DESCRIPTOR"):
            result[field.name] = proto_to_dict(value)

        elif getattr(field, "type", None) == 14:
            try:
                result[field.name] = field.enum_type.values_by_number[value].name
            except Exception:
                result[field.name] = value

        elif isinstance(value, bytes):
            result[field.name] = binascii.hexlify(value).decode("utf-8") if value else ""

        else:
            result[field.name] = value

    return result


# ============================================================
# Token extraction & normalization
# ============================================================

def extract_token(data):
    if not isinstance(data, dict):
        return None
    token = data.get("jwt_token") or data.get("token") or data.get("access_token")
    if token:
        return token
    nested = data.get("data")
    if isinstance(nested, dict):
        token = nested.get("jwt_token") or nested.get("token") or nested.get("access_token")
        if token:
            return token
    return None


def normalize_token(token):
    if not token:
        return None
    token = str(token).strip()
    if token.startswith("Bearer "):
        return token[7:].strip()
    return token


def get_region_jwt(region):
    region = region.upper()
    pool_key = "IND" if region == "IND" else "OTHARS_SVR"
    cycle_pool = region_cycles.get(pool_key, region_cycles["IND"])
    c_lock = cycle_locks.get(pool_key, jwt_lock)

    with c_lock:
        account = next(cycle_pool)
    
    uid = account.get("uid")
    password = account.get("password")

    if not uid or not password:
        raise Exception(f"Credentials missing for region: {region}")

    try:
        response = http_session.get(
            IND_JWT_URL,
            params={"uid": uid, "password": password},
            timeout=4
        )
        response.raise_for_status()
        token = extract_token(response.json())
        if not token:
            logger.warning("[%s] Failed to fetch token for UID: %s, rotating...", region, uid)
            return get_region_jwt(region)
        return normalize_token(token)
    except requests.exceptions.RequestException as e:
        logger.error("[%s] JWT provider error: %s", region, e)
        raise


def ensure_jwt_token_sync(region, force_refresh=False):
    region = (region or "IND").upper()
    now = time.time()

    if not force_refresh and region in jwt_tokens and now < jwt_expiry.get(region, 0):
        return jwt_tokens[region]

    with jwt_lock:
        now = time.time()
        if not force_refresh and region in jwt_tokens and now < jwt_expiry.get(region, 0):
            return jwt_tokens[region]

        token = get_region_jwt(region)
        jwt_tokens[region] = token
        jwt_expiry[region] = time.time() + JWT_CACHE_SECONDS
        return token


def get_api_endpoint(region):
    endpoints = {
        "IND": "https://client.ind.freefiremobile.com/GetPlayerPersonalShow",
        "BR": "https://client.us.freefiremobile.com/GetPlayerPersonalShow",
        "US": "https://client.us.freefiremobile.com/GetPlayerPersonalShow",
        "SAC": "https://client.us.freefiremobile.com/GetPlayerPersonalShow",
        "NA": "https://client.us.freefiremobile.com/GetPlayerPersonalShow",
        "BD": "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow",
        "ID": "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow",
        "PK": "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow",
        "VN": "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow",
        "ME": "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow",
        "TH": "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow"
    }
    return endpoints.get(region, endpoints["BD"])


def encrypt_aes(hex_data, key, iv):
    key_bytes = key.encode()[:16]
    iv_bytes = iv.encode()[:16]
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
    padded_data = pad(bytes.fromhex(hex_data), AES.block_size)
    return binascii.hexlify(cipher.encrypt(padded_data)).decode()


def make_headers(token):
    return {
        "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "Accept": "*/*",
        "Accept-Encoding": "deflate, gzip",
        "X-Ga-Sv": "1789534056",
        "Authorization": f"Bearer {normalize_token(token)}",
        "X-Ga": "v1 1",
        "Releaseversion": RELEASE_VERSION,
        "Content-Type": "application/octet-stream",
        "X-Unity-Version": "2018.4.12f1",
        "PlAy_VeR": "1.132.1",
        "Ob_VeR": RELEASE_VERSION
    }


def apis(encrypted_hex, region):
    region = (region or "IND").upper()
    endpoint = get_api_endpoint(region)

    for attempt in range(2):
        token = ensure_jwt_token_sync(region, force_refresh=(attempt > 0))
        headers = make_headers(token)
        try:
            response = http_session.post(
                endpoint,
                headers=headers,
                data=bytes.fromhex(encrypted_hex),
                timeout=6
            )
            if response.status_code in [401, 429]:
                logger.warning("[%s] Received status %s, rotating account...", region, response.status_code)
                jwt_tokens.pop(region, None)
                jwt_expiry.pop(region, None)
                continue
            response.raise_for_status()
            return response.content.hex()
        except requests.exceptions.RequestException:
            if attempt == 1:
                raise
    raise Exception("API request failed after rotation attempts")


def add_metadata(result, start_time):
    if not isinstance(result, dict):
        return result
    result["Devloper"] = "KHUSHI"
    result["Telegram"] = "myselfkhushi03"
    result["Time_Spne"] = f"{time.time() - start_time:.2f}s"
    result["Time"] = get_formatted_time()
    return result


# ============================================================
# Routes
# ============================================================

@app.route("/", methods=["GET"])
def home():
    return """<!DOCTYPE html><html><body><h3>Free Fire API Running</h3></body></html>"""


@app.route("/info", methods=["GET"])
def get_player_info():
    start_time = time.time()
    try:
        uid = request.args.get("uid")
        region = request.args.get("region", "IND").upper()
        custom_key = request.args.get("key", DEFAULT_KEY)
        custom_iv = request.args.get("iv", DEFAULT_IV)

        if not uid:
            return jsonify({"error": "UID parameter is required"}), 400
        try:
            uid_int = int(uid)
        except ValueError:
            return jsonify({"error": "Invalid UID format"}), 400

        message = uid_generator_pb2.uid_generator()
        message.saturn_ = uid_int
        message.garena = 1
        protobuf_data = message.SerializeToString()
        hex_data = binascii.hexlify(protobuf_data).decode()

        encrypted_hex = encrypt_aes(hex_data, custom_key, custom_iv)
        api_response = apis(encrypted_hex, region)

        if not api_response:
            return jsonify({"error": "Empty response from API"}), 502

        message = AccountPersonalShowInfo()
        message.ParseFromString(bytes.fromhex(api_response))
        result = proto_to_dict(message)
        add_metadata(result, start_time)

        return jsonify(result), 200

    except Exception as e:
        logger.exception("[INFO ERROR] %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/bot-status", methods=["GET"])
def bot_status():
    """Naya endpoint jo bot aur loaded accounts ki live status batayega"""
    regions_info = {}
    for region, accounts in REGION_ACCOUNTS.items():
        regions_info[region] = {
            "total_loaded_accounts": len(accounts),
            "token_cached": region in jwt_tokens and time.time() < jwt_expiry.get(region, 0)
        }

    return jsonify({
        "status": "online",
        "service": "Free Fire Player Info API Bot",
        "developer": "KHUSHI",
        "telegram": "myselfkhushi03",
        "regions": regions_info,
        "time": get_formatted_time()
    }), 200


@app.route("/favicon.ico")
def favicon():
    return "", 404


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "Free Fire Player Info API",
        "time": get_iso_time()
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "1080")),
        threaded=True
    )
    