import { NextRequest } from 'next/server';
import { adminAuth } from '@/lib/firebaseAdmin';

export interface ServerAuthUser {
  uid: string;
  email: string | null;
  displayName: string | null;
  photoURL: string | null;
  emailVerified: boolean;
}

/**
 * Get authenticated user from Authorization header.
 * Verifies the Firebase ID token via the Admin SDK (signature + expiry checked
 * against Google's public keys) rather than trusting the decoded payload.
 */
export async function getServerAuthUser(request: NextRequest): Promise<ServerAuthUser | null> {
  try {
    const authHeader = request.headers.get('authorization');

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return null;
    }

    const token = authHeader.substring(7); // Remove "Bearer " prefix

    if (!token) {
      return null;
    }

    try {
      const decoded = await adminAuth().verifyIdToken(token);

      return {
        uid: decoded.uid,
        email: decoded.email ?? null,
        displayName: decoded.name ?? null,
        photoURL: decoded.picture ?? null,
        emailVerified: decoded.email_verified ?? false,
      };
    } catch (tokenError) {
      console.error('Error verifying token:', tokenError);
      return null;
    }
  } catch (error) {
    console.error('Error getting auth user:', error);
    return null;
  }
}

/**
 * Get authenticated user ID from request
 */
export async function getServerAuthUserId(request: NextRequest): Promise<string | null> {
  const user = await getServerAuthUser(request);
  return user?.uid || null;
}

/**
 * Middleware helper to ensure user is authenticated
 */
export async function requireAuth(request: NextRequest): Promise<ServerAuthUser> {
  const user = await getServerAuthUser(request);
  
  if (!user) {
    throw new Error('Authentication required');
  }
  
  return user;
}
