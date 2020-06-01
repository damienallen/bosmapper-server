FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8 as development

# Install linux dependencies
RUN apt-get install xvfb libfontconfig wkhtmltopdf

# Install Poetry
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | POETRY_HOME=/opt/poetry python && \
  cd /usr/local/bin && \
  ln -s /opt/poetry/bin/poetry && \
  poetry config virtualenvs.create false

# Copy using poetry.lock* in case it doesn't exist yet
WORKDIR /pysetup
COPY ./pyproject.toml ./poetry.lock* /pysetup/
RUN poetry install --no-root --no-dev
WORKDIR /app

# Copy files in production
FROM development as production
COPY ./app /app
