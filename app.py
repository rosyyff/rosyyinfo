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
    "https://rosyyjwtgenrator.vercel.app/token"
)


# ============================================================
# Multi-Server Credentials Pools
# ============================================================

REGION_ACCOUNTS = {
    "IND": [
        {
            "uid": os.getenv("IND_UID_1", "8437554878"),
            "password": os.getenv("IND_PASS_1", "Mimiii755U5CFV3SFAH5BEZCIMYFW9GI"),
        },
        {
            "uid": os.getenv("IND_UID_2", "8437555612"),
            "password": os.getenv("IND_PASS_2", "MimiiiTVA16WH1VQIGK83SDKAVEX5RHL"),
        },
        {
            "uid": os.getenv("IND_UID_3", "8437554835"),
            "password": os.getenv("IND_PASS_3", "MimiiiG57KD2AASNPLYP55BMGIWWHQ89"),
        },
        {
            "uid": os.getenv("IND_UID_4", "8437554914"),
            "password": os.getenv("IND_PASS_4", "MimiiiOMPYH32BEZVI5QG535CZY4LFWT"),
        },
        {
            "uid": os.getenv("IND_UID_5", "8437555685"),
            "password": os.getenv("IND_PASS_5", "Mimiii1Q1N5LXZ7QVAG1SPY8YWM8YIDT"),
        },
        {
            "uid": os.getenv("IND_UID_6", "8437555691"),
            "password": os.getenv("IND_PASS_6", "MimiiiR2L3NXGNI4PAB3CIXO8LOSBOBP"),
        },
        {
            "uid": os.getenv("IND_UID_7", "8437555957"),
            "password": os.getenv("IND_PASS_7", "MimiiiIZBC427N0J0LYKB7VFREF3MFG7"),
        },
        {
            "uid": os.getenv("IND_UID_8", "8437555820"),
            "password": os.getenv("IND_PASS_8", "Mimiii81J8P1536CRJDNMWAW0SLWDFTS"),
        },
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
            timeout=4  # Reduced timeout to prevent hanging threads
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
    result["Devloper"] = "XEROX_MODS"
    result["Telegram"] = "SEXTYMODS"
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
