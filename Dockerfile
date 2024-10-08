FROM docker-registry.ebrains.eu/hdc-services-image/base-image:python-3.10.14-v1 AS download-image

ENV POETRY_VERSION=1.3.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false

ENV PATH="${POETRY_HOME}/bin:${PATH}"

RUN curl -sSL https://install.python-poetry.org | python3 -

COPY poetry.lock pyproject.toml ./
COPY app ./app
RUN poetry install --no-dev --no-root --no-interaction

RUN chown -R app:app /app
USER app

CMD ["python3", "-m", "app"]
