import unittest

from src.Services import ComposeService, ProxyComposeService, PostgresComposeService, KwkhtmltopdfComposeService, \
    IMAGE_KWKHTMLTOPDF, POSTGRES_DB, OdooComposeService


class TestComposeService(unittest.TestCase):

    def test_init_and_to_dict(self):
        service = ComposeService('test_service', 'test_image', test_key='test_value', none_key=None)
        expected_config = {
            'image': 'test_image',
            'container_name': 'test_service',
            'test_key': 'test_value'
        }
        self.assertEqual(service.to_dict(), expected_config)

    def test_to_dict_filters_none(self):
        service = ComposeService('test_service', 'test_image', test_key=None)
        expected_config = {
            'image': 'test_image',
            'container_name': 'test_service',
        }
        self.assertEqual(service.to_dict(), expected_config)


class TestProxyComposeService(unittest.TestCase):

    def test_init(self):
        proxy_service = ProxyComposeService('proxy', 'test.com', dashboard=True)
        self.assertIn('traefik.enable=true', proxy_service.to_dict()['labels'])
        self.assertIn('--api.dashboard=true', proxy_service.to_dict()['command'])


class TestOdooComposeService(unittest.TestCase):

    def test_init(self):
        odoo_service = OdooComposeService('odoo', 'odoo.test.com', 'db_pass', 'admin_pass')
        self.assertIn('DB_PASSWORD=db_pass', odoo_service.to_dict()['environment'])
        self.assertIn('ADMIN_PASSWD=admin_pass', odoo_service.to_dict()['environment'])


class TestPostgresComposeService(unittest.TestCase):

    def test_init(self):
        postgres_service = PostgresComposeService('postgres')
        self.assertIn(f'POSTGRES_DB={POSTGRES_DB}', postgres_service.to_dict()['environment'])


class TestKwkhtmltopdfComposeService(unittest.TestCase):

    def test_init(self):
        kwk_service = KwkhtmltopdfComposeService('kwk')
        self.assertEqual(kwk_service.to_dict()['image'], IMAGE_KWKHTMLTOPDF)


if __name__ == '__main__':
    unittest.main()
