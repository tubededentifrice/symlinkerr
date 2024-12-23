FROM python:latest

# Define a build-time argument for IMAGE_TAG
ARG IMAGE_TAG
ARG SHORT_COMMIT_ID

# Set an environment variable using the build-time argument
ENV IMAGE_TAG=$IMAGE_TAG
ENV SHORT_COMMIT_ID=$SHORT_COMMIT_ID

LABEL org.opencontainers.image.source="https://github.com/tubededentifrice/symlinkerr"
                                                      
ENV IS_IN_DOCKER=1

WORKDIR /app

COPY . .
RUN apt update && apt install -y python3-yaml
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python3", "symlinkerr.py", "watch"]
