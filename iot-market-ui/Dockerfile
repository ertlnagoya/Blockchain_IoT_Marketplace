# builder image
FROM node:latest AS builder

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci

COPY . .

RUN npm run build

RUN npm prune --production

# production image
FROM gcr.io/distroless/nodejs20-debian12

# we need "build", "package.json" and "node_modules(production dependencies)" for run application
COPY --from=builder /app/build build
COPY --from=builder /app/node_modules node_modules
COPY package.json .

USER nonroot
EXPOSE 3000

ENV NODE_ENV=production

CMD [ "build" ]
