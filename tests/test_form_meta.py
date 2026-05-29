from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient
from wtforms import StringField

from starlette_wtf import CSRFProtectMiddleware, StarletteForm


class MetaForm(StarletteForm):
    name = StringField()


def make_app(route):
    """Build a CSRF-enabled app exposing `route` at '/'.
    """
    app = Starlette(middleware=[
        Middleware(SessionMiddleware, secret_key='xxx'),
        Middleware(CSRFProtectMiddleware, csrf_secret='yyy')
    ])
    app.add_route('/', methods=['GET'], route=route)
    return TestClient(app)


def test_caller_meta_is_preserved():
    """Caller-supplied `meta` options survive the CSRF settings merge.
    """
    async def index(request):
        form = MetaForm(request, meta={'custom_option': 'kept'})

        # caller's option is preserved ...
        assert form.meta.custom_option == 'kept'

        # ... and the CSRF settings are still applied
        assert form.meta.csrf is True
        assert form.meta.csrf_field_name == 'csrf_token'
        assert hasattr(form, 'csrf_token')

        return PlainTextResponse()

    make_app(index).get('/')


def test_csrf_settings_override_caller_meta():
    """CSRF settings take precedence over conflicting caller `meta` keys.
    """
    async def index(request):
        form = MetaForm(request, meta={'csrf': False,
                                       'csrf_field_name': 'spoofed'})

        assert form.meta.csrf is True
        assert form.meta.csrf_field_name == 'csrf_token'

        return PlainTextResponse()

    make_app(index).get('/')


def test_meta_none_does_not_raise():
    """Passing `meta=None` is handled gracefully.
    """
    async def index(request):
        form = MetaForm(request, meta=None)
        assert form.meta.csrf is True
        return PlainTextResponse()

    make_app(index).get('/')


def test_caller_meta_dict_is_not_mutated():
    """The caller's `meta` dict is copied, not modified in place.
    """
    async def index(request):
        original = {'custom_option': 'kept'}
        MetaForm(request, meta=original)
        assert original == {'custom_option': 'kept'}
        return PlainTextResponse()

    make_app(index).get('/')


def test_no_csrf_config_leaves_meta_untouched():
    """Without CSRF middleware the caller's `meta` is passed through as-is.
    """
    app = Starlette()

    async def index(request):
        form = MetaForm(request, meta={'custom_option': 'kept'})
        assert form.meta.custom_option == 'kept'
        assert form.meta.csrf is False
        return PlainTextResponse()

    app.add_route('/', methods=['GET'], route=index)
    TestClient(app).get('/')
