// src/lib/firebase.ts

import { initializeApp, getApps, getApp } from "firebase/app";
import { getAnalytics, isSupported, Analytics } from "firebase/analytics";
import { connectAuthEmulator, getAuth } from "firebase/auth";
import { connectFirestoreEmulator, getFirestore } from "firebase/firestore";
import { getStorage } from "firebase/storage";

// Firebase configuration using environment variables
const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
  measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID,
};

// Initialize Firebase safely
const app = !getApps().length ? initializeApp(firebaseConfig) : getApp();

// Firebase services
export const auth = getAuth(app);
export const db = getFirestore(app);
export const storage = getStorage(app);

// Fully offline install: talk to the Firebase emulators (docker-compose.offline.yml) instead of Google.
// The browser reaches them on the same machine that serves the app unless a host is given.
if (process.env.NEXT_PUBLIC_USE_FIREBASE_EMULATOR === "true" && typeof window !== "undefined") {
  const host = process.env.NEXT_PUBLIC_FIREBASE_EMULATOR_HOST || window.location.hostname;
  const flag = "__flowmindEmulatorsConnected";
  if (!(window as any)[flag]) {   // connect*Emulator throws if called twice (hot reload)
    connectAuthEmulator(auth, `http://${host}:9099`, { disableWarnings: true });
    connectFirestoreEmulator(db, host, 8080);
    (window as any)[flag] = true;
  }
}

// Analytics (client-side only). Skipped on an offline install: it phones Google with a fake key and its
// retries stalled sign-up by over a minute.
export let analytics: Analytics | null = null;

if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_USE_FIREBASE_EMULATOR !== "true") {
  isSupported()
    .then((supported) => {
      if (supported) {
        analytics = getAnalytics(app);
        console.log("✅ Firebase Analytics initialized");
      }
    })
    .catch((error) => {
      console.warn("⚠️ Firebase Analytics not supported:", error);
    });
}

export default app;