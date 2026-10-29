# Local stand-in for Firebase Auth + Firestore, so FlowMind runs with NO internet and no Google account.
# Build context is the repository root (it needs firebase.json and firestore.rules).
FROM node:20-bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends openjdk-17-jre-headless ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN npm install -g firebase-tools@13

WORKDIR /srv
COPY firebase.json firestore.rules ./

# Download the Firestore emulator now (needs internet at BUILD time only) so the container
# starts and runs without it. The Auth emulator ships inside firebase-tools.
RUN firebase setup:emulators:firestore

COPY deploy/firebase-emulator/start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 9099 8080
VOLUME /data
CMD ["/start.sh"]
