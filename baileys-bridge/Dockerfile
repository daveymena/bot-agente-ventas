# Puente de WhatsApp (Baileys)
FROM node:20-alpine

WORKDIR /app

RUN apk add --no-cache curl

COPY package*.json ./
RUN npm install --omit=dev --no-audit --no-fund

COPY . .

# La sesión de WhatsApp vive aquí: móntalo como volumen para no re-escanear el QR
ENV BAILEYS_AUTH_DIR=/data/auth
VOLUME ["/data"]

EXPOSE 3001
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD curl -fsS http://localhost:3001/health || exit 1

CMD ["node", "index.js"]
