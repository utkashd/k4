FROM node:23-alpine AS builder
WORKDIR /app

COPY package.json /app
COPY package-lock.json /app
RUN npm install

ARG K4_ENVIRONMENT
ENV K4_ENVIRONMENT=${K4_ENVIRONMENT}
ARG IN_CONTAINER
ENV IN_CONTAINER=${IN_CONTAINER}
# vite + react handles environment variables differently. We have to
# write them to a .env file before building, and they all must start
# with `VITE_`. Then they are accessed via `import.meta.env.VITE_...`
# Also, all the environment variables loaded that way are
# public, so don't put anything remotely sensitive there
RUN echo "VITE_K4_ENVIRONMENT=${K4_ENVIRONMENT}" > .env && \
    echo "VITE_IN_CONTAINER=${IN_CONTAINER}" >> .env

COPY . /app
RUN npm run build

FROM nginx:stable-alpine
# Anthony Sottile says this line should be in every Dockerfile:
ENV LANG=C.UTF-8
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
ENTRYPOINT ["nginx", "-g", "daemon off;"]
