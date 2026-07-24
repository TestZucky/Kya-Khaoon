# Dev image: compose bind-mounts the source over /app for Vite HMR, with an
# anonymous volume keeping /app/node_modules from being shadowed by the host.
FROM node:22-alpine

WORKDIR /app

# Lockfile-only install layer, so editing a component never reinstalls deps.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173
# --host binds 0.0.0.0; without it Vite listens on loopback inside the container
# and the published port answers nothing.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
