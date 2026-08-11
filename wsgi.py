import sys

if "gevent" in sys.argv:
    from gevent import monkey

    monkey.patch_all()

from cpf_fcv_reviewer.app import create_app

app = create_app()
