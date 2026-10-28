# Alamat backend dibaca saat build (rewrites Next.js), jadi diatur sebagai build arg.
FROM node:22-alpine AS build
ARG FLASK_BACKEND_URL=http://backend:5000
ENV FLASK_BACKEND_URL=$FLASK_BACKEND_URL
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
