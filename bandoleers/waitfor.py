"""

wait-for -- wait for a URL to become available

Usage:
    wait-for <URL> [--timeout=seconds] [-v |--verbose]
    wait-for (-h | --help | --version)

"""
import asyncore
import logging
import socket
import sys
import time
try:
    from urllib import parse
except ImportError:
    import urlparse as parse

from cassandra import cluster
import docopt
import requests.exceptions


logging.basicConfig(
    level=logging.ERROR,
    format='%(relativeCreated)-10d %(levelname)-8s %(message)s')
LOGGER = logging.getLogger(__name__)


def connect_to(url, timeout):
    scheme, netloc, path, query, fragment = parse.urlsplit(url)
    if scheme in ('http', 'https'):
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return True

    elif scheme == 'cassandra':
        host, _, port = netloc.partition(':')
        _, _, ip_addrs = socket.gethostbyname_ex(host)
        conn = cluster.Cluster(contact_points=ip_addrs, port=int(port) or 9042,
                               control_connection_timeout=timeout)
        conn.connect()
        asyncore.close_all()
        asyncore.loop()

        return True

    else:
        raise RuntimeError("I don't know what to do with {0}".format(scheme))


def run():
    logger = logging.getLogger(__name__)
    opts = docopt.docopt(__doc__)
    timeout = opts.get('--timeout', None)
    sleep_time = 0.25

    if opts.get('--verbose', False) or opts.get('-v', False):
        logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger('cassandra').setLevel(logging.CRITICAL)

    t0 = time.time()
    wait_forever = timeout is None
    timeout = 0.25 if wait_forever else float(timeout)
    logger.debug('waiting for %s', 'forever' if wait_forever else timeout)
    while wait_forever or (time.time() - t0) < timeout:
        try:
            if connect_to(opts['<URL>'], timeout=timeout):
                logger.debug('connection to %s succeeded after %f seconds',
                             opts['<URL>'], time.time() - t0)
                sys.exit(0)

        except RuntimeError:
            logger.exception('internal failure')
            sys.exit(70)

        except KeyboardInterrupt:
            logger.info('killed')
            sys.exit(-1)

        except Exception as error:
            logger.debug('%s, sleeping for %f seconds', error, sleep_time)
            time.sleep(sleep_time)

    logger.error('wait timed out after %f seconds', time.time() - t0)
    sys.exit(-1)