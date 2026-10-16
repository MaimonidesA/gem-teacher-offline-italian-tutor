"""Optional LAN sharing and local TLS. No public services or certificate calls."""
import ipaddress
import json
import logging
import os
from pathlib import Path
import ssl
import subprocess
import tempfile

from . import config

PRIVATE = tuple(ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))


def enabled():
    if "PARLIAMO_LAN" in os.environ:
        return os.environ["PARLIAMO_LAN"] == "1"
    try:
        return json.loads((config.DATA / "network.json").read_text()).get("lan") is True
    except (OSError, ValueError):
        return False


def save_enabled(value):
    config.prepare()
    path = config.DATA / "network.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"lan": bool(value)}))
    temporary.replace(path)


def interfaces():
    """Private IPv4 Ethernet/Wi-Fi subnets, excluding VPNs and virtual bridges."""
    try:
        rows = json.loads(subprocess.check_output(["ip", "-j", "-4", "addr", "show", "up"], timeout=3))
    except (OSError, ValueError, subprocess.SubprocessError):
        return []
    result = []
    for row in rows:
        if (set(row.get("flags", [])) & {"LOOPBACK", "POINTOPOINT"}
                or row.get("ifname", "").startswith(("docker", "veth", "br-", "virbr", "tun", "tap", "wg", "tailscale", "zt"))):
            continue
        for address in row.get("addr_info", []):
            if address.get("family") != "inet":
                continue
            ip = ipaddress.ip_address(address["local"])
            if any(ip in subnet for subnet in PRIVATE):
                result.append(ipaddress.ip_interface(f"{ip}/{address['prefixlen']}"))
    return result


def client_allowed(address, local_interfaces):
    try:
        ip = ipaddress.ip_address(address)
        return ip.is_loopback or any(ip in interface.network for interface in local_interfaces)
    except ValueError:
        return False


def watch_interfaces(initial, on_change, stopped, interval=5):
    """Recover after startup without Wi-Fi, reconnects and DHCP address changes."""
    previous = tuple(sorted(initial, key=str))
    while not stopped.wait(interval):
        try:
            current = tuple(sorted(interfaces(), key=str))
            if current != previous:
                on_change(current)
                previous = current
        except (OSError, ValueError, subprocess.SubprocessError):
            # Keep retrying if certificate renewal or interface discovery fails.
            logging.exception("Could not refresh phone access; retrying shortly")


def prepare_tls(local_interfaces, context=None):
    """Keep one private CA; renew the server certificate when the LAN IP changes."""
    folder = config.DATA / "tls"
    folder.mkdir(mode=0o700, exist_ok=True)
    folder.chmod(0o700)
    ca, ca_key = folder / "phone-ca.crt", folder / "ca.key"
    cert, key = folder / "server.crt", folder / "server.key"
    hosts = sorted({"127.0.0.1", *(str(i.ip) for i in local_interfaces)})

    def openssl(*args):
        return subprocess.check_output(["openssl", *map(str, args)], stderr=subprocess.PIPE, timeout=30)

    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        tmp = Path(temporary)
        if not ca.exists() and not ca_key.exists():
            openssl("req", "-x509", "-newkey", "rsa:3072", "-nodes", "-sha256", "-days", "3650",
                    "-subj", "/CN=Gem Teacher Local CA", "-addext", "basicConstraints=critical,CA:TRUE,pathlen:0",
                    "-addext", "keyUsage=critical,keyCertSign,cRLSign", "-keyout", tmp / "ca.key", "-out", tmp / "ca.crt")
            (tmp / "ca.key").chmod(0o600)
            (tmp / "ca.key").replace(ca_key)
            (tmp / "ca.crt").replace(ca)
        if not ca.is_file() or not ca_key.is_file():
            raise ValueError("Local TLS certificate files are incomplete; restore data/tls from your backup.")
        ca_key.chmod(0o600)
        recorded = folder / "addresses.json"
        renew = not (cert.exists() and key.exists() and recorded.exists())
        if not renew:
            renew = json.loads(recorded.read_text()) != hosts
            if not renew:
                renew = subprocess.run(["openssl", "x509", "-checkend", "86400", "-noout", "-in", str(cert)],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10).returncode != 0
        if renew:
            openssl("req", "-new", "-newkey", "rsa:2048", "-nodes", "-sha256", "-subj", "/CN=Gem Teacher",
                    "-keyout", tmp / "server.key", "-out", tmp / "server.csr")
            extensions = tmp / "extensions.cnf"
            extensions.write_text("basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\n"
                                  "extendedKeyUsage=serverAuth\nsubjectAltName=DNS:localhost," + ",".join("IP:" + h for h in hosts) + "\n")
            openssl("x509", "-req", "-in", tmp / "server.csr", "-CA", ca, "-CAkey", ca_key,
                    "-set_serial", "0x" + os.urandom(16).hex(), "-days", "365", "-sha256",
                    "-extfile", extensions, "-out", tmp / "server.crt")
            (tmp / "server.key").chmod(0o600)
            (tmp / "server.key").replace(key)
            (tmp / "server.crt").replace(cert)
            recorded.write_text(json.dumps(hosts))
        key.chmod(0o600)
    if context is None:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
    # Reload the listener's existing context: new connections use the renewed
    # certificate, while established phone connections can finish normally.
    context.load_cert_chain(cert, key)
    return context
