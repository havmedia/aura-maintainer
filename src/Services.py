IMAGE_TRAEFIK = 'registry.hav.media/aura_odoo/traefik:v2.10'
IMAGE_ODOO = 'registry.hav.media/aura_odoo/odoo'
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
    def __init__(self, name: str, domain: str, dashboard: bool = False, https=True, **kwargs):
        config = {
            'name': name,
            'image': IMAGE_TRAEFIK,
            'restart': 'always',
            'command': [
                '--providers.docker=true',
                '--providers.docker.exposedbydefault=false',
                '--providers.file.directory=/etc/traefik',
                '--entrypoints.websecure.address=:443',
                '--entrypoints.web.address=:80',
                '--certificatesresolvers.main_resolver.acme.tlschallenge=true',
                # TODO: Make configurable
                '--certificatesresolvers.main_resolver.acme.email=accounts@hav.media',
                '--certificatesresolvers.main_resolver.acme.storage=/letsencrypt/acme.json',
                '--ping',
            ],
            'ports': [
                '80:80',
                '443:443'
            ],
            'volumes': [
                '/var/run/docker.sock:/var/run/docker.sock',
                f'./volumes/{name}/letsencrypt:/letsencrypt'
            ],
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

        if https:
            config['command'] += [
                "--entrypoints.web.http.redirections.entrypoint.to=websecure",
                "--entrypoints.web.http.redirections.entrypoint.scheme=https"
            ]

        if dashboard:
            config['labels'] += [
                'traefik.enable=true',
                f'traefik.http.routers.proxy.rule=Host(`proxy.{domain}`)',
                f'traefik.http.routers.proxy.entrypoints={"websecure" if https else "web"}',
                'traefik.http.routers.proxy.service=api@internal',
                'traefik.http.routers.proxy.middlewares=basic_auth@file'
            ]
            config['command'] += [
                '--api.dashboard=true',
            ]

            if https:
                config['labels'].append('traefik.http.routers.proxy.tls.certresolver=main_resolver')

        config.update(kwargs)
        super().__init__(**config)


class OdooComposeService(ComposeService):
    def __init__(self, name: str, domain: str, db_password: str, admin_passwd: str, odoo_version: str,
                 basic_auth: bool = True, https: bool = True, module_mode: str = 'included', **kwargs):
        config = {
            'name': name,
            'image': f'{IMAGE_ODOO}:{odoo_version}',
            'restart': 'always',
            'environment': {
                'DB_NAME': name,
                'DB_USER': name,
                'DB_PASSWORD': db_password,
                'DB_HOST': 'db',
                'ADMIN_PASSWD': admin_passwd,
                'ADDONS_PATH': '/odoo/src/odoo/addons, /odoo/src/enterprise'
            },
            'labels': {
                'traefik.enable': 'true',
                f'traefik.http.routers.{name}.rule': f'Host(`{domain}`)',
                f'traefik.http.routers.{name}.service': name,
                f'traefik.http.routers.{name}.priority': '1',
                f'traefik.http.routers.{name}.entrypoints': 'websecure' if https else 'web',
                f'traefik.http.services.{name}.loadbalancer.server.port': '8069',
                # Websocket
                f'traefik.http.routers.{name}-websocket.rule': f'Path(`/websocket`) && Host(`{domain}`)',
                f'traefik.http.routers.{name}-websocket.priority': '2',
                f'traefik.http.routers.{name}-websocket.service': f'{name}-websocket',
                f'traefik.http.routers.{name}-websocket.entrypoints': 'websecure' if https else 'web',
                f'traefik.http.services.{name}-websocket.loadbalancer.server.port': '8072',
            },
            'depends_on': [
                'db',
                'proxy',
                'kwkhtmltopdf'
            ],
            'volumes': [
                f'./volumes/{name}:/data/odoo/',
            ]
        }

        if https:
            config['labels'] |= {
                f'traefik.http.routers.{name}-websocket.tls.certresolver': 'main_resolver',
                f'traefik.http.routers.{name}.tls.certresolver': 'main_resolver',
            }

        if module_mode == 'mounted':
            config['volumes'] += [
                f'./volumes/{name}/src:/odoo/src/'
            ]

        if basic_auth:
            config['labels'] |= {
                f'traefik.http.routers.odoo_{name}.middlewares': 'basic_auth@file,gzip@file',
                f'traefik.http.routers.odoo_{name}-websocket.middlewares': 'basic_auth@file,websocketHeader@file,gzip@file',
            }
        else:
            config['labels'] |= {
                f'traefik.http.routers.odoo_{name}.middlewares': 'gzip@file',
                f'traefik.http.routers.odoo_{name}-websocket.middlewares': 'websocketHeader@file,gzip@file',
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
            'environment': {
                'POSTGRES_DB': POSTGRES_DB,
                'POSTGRES_PASSWORD': '${MASTER_DB_PASSWORD}',
                'POSTGRES_USER': POSTGRES_USER
            },
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
