IMAGE_TRAEFIK = 'registry.hav.media/aura_odoo/traefik:v2.10'
IMAGE_WHOAMI = 'registry.hav.media/aura_odoo/odoo:16.0'
IMAGE_KWKHTMLTOPDF = 'registry.hav.media/aura_odoo/kwkhtmltopdf:0.12.5'
IMAGE_POSTGRES = 'registry.hav.media/aura_odoo/postgres:15-alpine'

POSTGRES_PORT = 5432
POSTGRES_USER = 'postgres'
POSTGRES_DB = 'postgres'


class ComposeService:
    def __init__(self, name: str, image: str, **kwargs):
        self.name = name
        self.image = image
        self.extra_config = kwargs

    def to_dict(self) -> dict:
        return {key: value for key, value in {
            'image': self.image,
            'container_name': self.name,
            **self.extra_config
        }.items() if value is not None}  # Remove None Values


class ProxyComposeService(ComposeService):
    def __init__(self, name: str, domain: str, dashboard: bool = False, **kwargs):
        config = {
            'name': name,
            'image': IMAGE_TRAEFIK,
            'restart': 'always',
            'command': [
                '--providers.docker=true',
                '--providers.docker.exposedbydefault=false',
                '--providers.file.directory=/etc/traefik',
                '--entrypoints.web.address=:80',
                '--ping'
            ],
            'ports': ['80:80'],
            'volumes': ['/var/run/docker.sock:/var/run/docker.sock'],
            'healthcheck': {
                'test': 'traefik healthcheck --ping',
                'interval': '5s',
                'timeout': '5s',
                'retries': 30
            },
            'labels': [
                # TODO: Add middleware for ip whitelist
            ]
        }

        if dashboard:
            config['labels'] += [
                'traefik.enable=true',
                f'traefik.http.routers.proxy.rule=Host(`proxy.{domain}`)',
                'traefik.http.routers.proxy.entrypoints=web',
                'traefik.http.routers.proxy.service=api@internal',
                'traefik.http.routers.proxy.middlewares=basic_auth@file',
            ]
            config['command'] += [
                '--api.dashboard=true',
            ]

        config.update(kwargs)
        super().__init__(**config)


class OdooComposeService(ComposeService):
    def __init__(self, name: str, domain: str, db_password: str, admin_passwd: str, **kwargs):
        config = {
            'name': name,
            'image': IMAGE_WHOAMI,
            'restart': 'always',
            'environment': [
                f'DB_NAME={name}',
                f'DB_USER={name}',
                f'DB_PASSWORD={db_password}',
                f'DB_HOST=db',

                f'ADMIN_PASSWD={admin_passwd}',

                'ADDONS_PATH=/odoo/src/odoo/addons, /odoo/src/enterprise'
            ],
            'labels': [
                'traefik.enable=true',
                f'traefik.http.routers.{name}.rule=Host(`{domain}`)',
                f'traefik.http.routers.{name}.service={name}',
                f'traefik.http.routers.{name}.entrypoints=web',
                f'traefik.http.routers.{name}.middlewares=basic_auth@file,gzip@file',
                f'traefik.http.services.{name}.loadbalancer.server.port=8069',
                # Websocket
                f'traefik.http.routers.{name}-websocket.rule=Path(`/websocket`) && Host(`{domain}`)',
                f'traefik.http.routers.{name}-websocket.service={name}-websocket',
                f'traefik.http.routers.{name}-websocket.entrypoints=web',
                f'traefik.http.routers.{name}-websocket.middlewares=basic_auth@file,websocketHeader@file,gzip@file',
                f'traefik.http.services.{name}-websocket.loadbalancer.server.port=8072',
            ],
            'depends_on': [
                'db',
                'proxy',
                'kwkhtmltopdf'
            ],
            'volumes': [
                f'./volumes/{name}:/data/odoo/'
            ]
        }
        config.update(kwargs)
        super().__init__(**config)


class PostgresComposeService(ComposeService):
    def __init__(self, name: str, **kwargs):
        config = {
            'name': name,
            'restart': 'always',
            'image': IMAGE_POSTGRES,
            'ports': [
                f'127.0.0.1:{POSTGRES_PORT}:{POSTGRES_PORT}'
            ],
            'environment': [
                f'POSTGRES_DB={POSTGRES_DB}',
                'POSTGRES_PASSWORD=${MASTER_DB_PASSWORD}',
                f'POSTGRES_USER={POSTGRES_USER}',
            ],
            'healthcheck': {
                'test': 'pg_isready -U postgres',
                'interval': '5s',
                'timeout': '5s',
                'retries': 5
            },
            'volumes': [
                './volumes/db:/var/lib/postgresql/data'
            ]
        }
        config.update(kwargs)
        super().__init__(**config)


class KwkhtmltopdfComposeService(ComposeService):
    def __init__(self, name: str, **kwargs):
        config = {
            'name': name,
            'restart': 'always',
            'image': IMAGE_KWKHTMLTOPDF,
            # TODO: Add healthcheck back in if pr https://github.com/acsone/kwkhtmltopdf/pull/13 is merged
            # 'healthcheck': {
            #     'test': 'curl --fail http://localhost:8080/status || exit 1',
            #     'interval': '5s',
            #     'timeout': '5s',
            #     'retries': 5
            # },
        }
        config.update(kwargs)
        super().__init__(**config)
