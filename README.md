# Download Service

[![Python](https://img.shields.io/badge/python-3.7-brightgreen.svg)](https://www.python.org/)

The upload service is one of the key component for PILOT project. It's built using the FastAPI python framework. The main responsibility is to handle the file/folder download from [Minio](https://min.io/) Object Storage. If api reqeusts to download multiple files or folder, the service will combine them as the zip file.

## Getting Started

This is an example of how to run the download service locally.

### Prerequisites

This project is using [Poetry](https://python-poetry.org/docs/#installation) to handle the dependencies.

    curl -sSL https://install.python-poetry.org | python3 -

### Installation & Quick Start

1. Clone the project.

       git clone https://github.com/PilotDataPlatform/download.git

2. Install dependencies.

       poetry install

3. Install any OS level dependencies if needed.

       apt install <required_package>
       brew install <required_package>

5. Add environment variables into `.env` in case it's needed. Use `.env.schema` as a reference.

6. Run application.

       poetry run python run.py

### Startup using Docker

This project can also be started using [Docker](https://www.docker.com/get-started/).

1. To build and start the service within the Docker container, run:

       docker compose up

## Contribution

You can contribute the project in following ways:

* Report a bug.
* Suggest a feature.
* Open a pull request for fixing issues or adding functionality. Please consider
  using [pre-commit](https://pre-commit.com) in this case.
* For general guidelines on how to contribute to the project, please take a look at the [contribution guides](CONTRIBUTING.md).

## Acknowledgements

The development of the HealthDataCloud open source software was supported by the EBRAINS research infrastructure, funded from the European Union's Horizon 2020 Framework Programme for Research and Innovation under the Specific Grant Agreement No. 945539 (Human Brain Project SGA3) and H2020 Research and Innovation Action Grant Interactive Computing E-Infrastructure for the Human Brain Project ICEI 800858.

This project has received funding from the European Union’s Horizon Europe research and innovation programme under grant agreement No 101058516. Views and opinions expressed are however those of the author(s) only and do not necessarily reflect those of the European Union or other granting authorities. Neither the European Union nor other granting authorities can be held responsible for them.

![HDC-EU-acknowledgement](https://hdc.humanbrainproject.eu/img/HDC-EU-acknowledgement.png)
