<a name="readme-top"></a>


<!-- PROJECT SHIELDS -->
[![LinkedIn][linkedin-shield]][linkedin-url]
[![Status Action][action-shield]][action-url]
<br><br>

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://hav.media">
    <img src="https://drive.google.com/uc?export=download&id=1PnNUC1JkUquDcKK9NIQYdKG6ZHY7Gj1h" alt="Logo" width="80" height="80">
  </a>

  <h3 align="center">Setup Maintainer for Project Aura</h3>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about">About</a>
    </li>
    <li>
      <a href="#commands">Commands</a>
    </li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About

This repo contains the python Setup Maintainer for odoo setups. It is used to setup and maintain odoo setups on a server.
<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Requirements
The script currently needs to be run as root.

## Commands

### init

The init command is used to initialize the setup maintainer. It will create a new setup maintainer project in the current directory.

You can provide the option `--dev` to run without ssh and reduced checks.
You can provide the option `--disable-domain-check` to disable the domain check.
```sh
aura-maintainer init DOMAIN VERSION
```

### Generate

The generate command is used to update the odoo setup. It will update the setup in the current /opt/odoo folder.

You can provide the option `--dashboard` to allow access to the traefik dashboard.
You can provide the option `--dry` to only show what would change in the docker compose file


```sh
aura-maintainer generate
```

### Inspect

The inspect command is used to inspect the current setup. It will print data about the current setup to the console.

You can provide the option `--json` to get the response as json.

```sh
aura-maintainer inspect
```

### Change Domain

The change domain command is used to change the domain of the current setup. It will update the setup in the current /opt/odoo folder.

```sh
aura-maintainer change_domain NEW_DOMAIN
```

### Refresh Environment

Copys the live database and filestore to the desired environment. The database gets escaped.

```sh
aura-maintainer refresh-env ENVIRONMENT
```

### Manage Dev Environments

The manage dev environments command provides multiple subcommands to manage the dev environments.

> [!CAUTION]
> This functions are obsolete and will be replaced.

#### add

The add command adds an dev enviroment.

```sh
aura-maintainer manage-dev-env add PR_NUMBER
```

#### remove

The remove command removes an dev enviroment.

```sh
aura-maintainer manage-dev-env remove PR_NUMBER
```

### remove-all

The remove-all command removes all dev envs.

```sh
aura-maintainer remove-all
```

<!-- CONTACT -->
## Contact

HAV Media GmbH - <a href="mailto:info@hav.media"/>info@hav.media</a>

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->

[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://www.linkedin.com/company/havmedia/

[action-shield]: https://img.shields.io/github/actions/workflow/status/havmedia/aura-maintainer/pylint.yml?style=for-the-badge
[action-url]: https://github.com/havmedia/aura-maintainer/actions/workflows/pylint.yml