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

        config_dict = odoo_service.to_dict()

        assert 'DB_PASSWORD' in config_dict['environment'] and 'db_pass' == \
               config_dict['environment']['DB_PASSWORD']
        assert 'ADMIN_PASSWD' in config_dict['environment'] and 'admin_pass' == \
               config_dict['environment']['ADMIN_PASSWD']
        assert config_dict['image'] == 'registry.hav.media/aura_odoo/odoo:16.0'

    def test_with_basic_auth(self):
        odoo_service = OdooComposeService('odoo', 'odoo.test.com', 'db_pass', 'admin_pass', '16.0', False)

        config_dict = odoo_service.to_dict()

        assert 'DB_PASSWORD' in config_dict['environment'] and 'db_pass' == \
               config_dict['environment']['DB_PASSWORD']
        assert 'ADMIN_PASSWD' in config_dict['environment'] and 'admin_pass' == \
               config_dict['environment']['ADMIN_PASSWD']
        assert 'traefik.http.routers.odoo_odoo-websocket.middlewares' in config_dict[
            'labels'] and 'websocketHeader@file,gzip@file' == config_dict['labels'][
                   'traefik.http.routers.odoo_odoo-websocket.middlewares']
        assert config_dict['image'] == 'registry.hav.media/aura_odoo/odoo:16.0'

    def test_with_module_mode_mounted(self):
        odoo_service = OdooComposeService('odoo', 'odoo.test.com', 'db_pass', 'admin_pass', '16.0', False,
                                          module_mode='mounted')

        config_dict = odoo_service.to_dict()

        assert 'DB_PASSWORD' in config_dict['environment'] and 'db_pass' == \
               config_dict['environment']['DB_PASSWORD']
        assert 'ADMIN_PASSWD' in config_dict['environment'] and 'admin_pass' == \
               config_dict['environment']['ADMIN_PASSWD']
        assert 'traefik.http.routers.odoo_odoo-websocket.middlewares' in config_dict[
            'labels'] and 'websocketHeader@file,gzip@file' == config_dict['labels'][
                   'traefik.http.routers.odoo_odoo-websocket.middlewares']
        assert config_dict['image'] == 'registry.hav.media/aura_odoo/odoo:16.0'
        assert './volumes/odoo/src:/odoo/src/' in config_dict['volumes']


class TestPostgresComposeService:

    def test_init(self):
        postgres_service = PostgresComposeService('postgres')
        assert 'POSTGRES_DB' in postgres_service.to_dict()['environment'] and POSTGRES_DB == postgres_service.to_dict()['environment']['POSTGRES_DB']


class TestKwkhtmltopdfComposeService:

    def test_init(self):
        kwk_service = KwkhtmltopdfComposeService('kwk')
        assert kwk_service.to_dict()['image'] == IMAGE_KWKHTMLTOPDF
