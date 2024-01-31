from src.Services import ComposeService, ProxyComposeService, PostgresComposeService, KwkhtmltopdfComposeService, \
    IMAGE_KWKHTMLTOPDF, POSTGRES_DB, OdooComposeService


class TestComposeService:

    def test_init_and_to_dict(self):
        service = ComposeService('test_service', 'test_image', test_key='test_value', none_key=None)
        expected_config = {
            'image': 'test_image',
            'container_name': 'test_service',
            'test_key': 'test_value'
        }
        assert service.to_dict() == expected_config

    def test_to_dict_filters_none(self):
        service = ComposeService('test_service', 'test_image', test_key=None)
        expected_config = {
            'image': 'test_image',
            'container_name': 'test_service',
        }
        assert service.to_dict() == expected_config


class TestProxyComposeService:

    def test_init(self):
        proxy_service = ProxyComposeService('proxy', 'test.com', dashboard=True)
        assert 'traefik.enable=true' in proxy_service.to_dict()['labels']
        assert '--api.dashboard=true' in proxy_service.to_dict()['command']



class TestOdooComposeService:

    def test_init(self):
        odoo_service = OdooComposeService('odoo', 'odoo.test.com', 'db_pass', 'admin_pass', '16.0')
        assert 'DB_PASSWORD=db_pass' in odoo_service.to_dict()['environment']
        assert 'ADMIN_PASSWD=admin_pass' in odoo_service.to_dict()['environment']
        assert odoo_service.to_dict()['image'] == 'registry.hav.media/aura_odoo/odoo:16.0'

    def test_with_basic_auth(self):
        odoo_service = OdooComposeService('odoo', 'odoo.test.com', 'db_pass', 'admin_pass', '16.0', False)
        assert 'DB_PASSWORD=db_pass' in odoo_service.to_dict()['environment']
        assert 'ADMIN_PASSWD=admin_pass' in odoo_service.to_dict()['environment']
        assert 'traefik.http.routers.odoo-websocket.middlewares=websocketHeader@file,gzip@file' in odoo_service.to_dict()['labels']
        assert odoo_service.to_dict()['image'] == 'registry.hav.media/aura_odoo/odoo:16.0'


class TestPostgresComposeService:

    def test_init(self):
        postgres_service = PostgresComposeService('postgres')
        assert f'POSTGRES_DB={POSTGRES_DB}' in postgres_service.to_dict()['environment']


class TestKwkhtmltopdfComposeService:

    def test_init(self):
        kwk_service = KwkhtmltopdfComposeService('kwk')
        assert kwk_service.to_dict()['image'] == IMAGE_KWKHTMLTOPDF
