"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Users, Mail, Shield, MoreHorizontal, UserPlus, X, Search, Check, AlertTriangle, Loader2 } from "lucide-react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";

import { db, auth } from "@/lib/firebase";
import { doc, getDoc, setDoc } from "firebase/firestore";

interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: 'Admin' | 'Editor' | 'Viewer';
  status: 'Active' | 'Pending';
  joinedAt: string;
}

export default function TeamView() {
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<'Admin' | 'Editor' | 'Viewer'>("Editor");
  const [searchTerm, setSearchTerm] = useState("");
  const [inviting, setInviting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTeamMembers = async () => {
    try {
      const user = auth.currentUser;
      if (!user) {
        setError("You must be signed in to view team members.");
        setLoading(false);
        return;
      }

      const uid = user.uid;
      const userDocRef = doc(db, "users", uid);
      const userDoc = await getDoc(userDocRef);

      // Always include the current user as owner
      const ownerMember: TeamMember = {
        id: uid,
        name: user.displayName || user.email || "You",
        email: user.email || "",
        role: "Admin",
        status: "Active",
        joinedAt: user.metadata.creationTime || new Date().toISOString(),
      };

      if (!userDoc.exists()) {
        // No user doc yet — just show the current user
        setMembers([ownerMember]);
        setLoading(false);
        return;
      }

      const userData = userDoc.data();
      const workspace = userData?.workspace || {};
      const storedMembers: any[] = workspace.members || [];

      const teamMembers: TeamMember[] = [ownerMember];

      for (const member of storedMembers) {
        teamMembers.push({
          id: member.id,
          name: member.name || member.email,
          email: member.email,
          role: member.role || "Viewer",
          status: member.status || "Pending",
          joinedAt: member.joinedAt,
        });
      }

      setMembers(teamMembers);
      setError(null);
    } catch (e: any) {
      console.error("Error fetching team members:", e);
      setError(e.message || "Failed to load team members");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Wait for auth state to be ready
    const unsubscribe = auth.onAuthStateChanged((user) => {
      if (user) {
        fetchTeamMembers();
      } else {
        setLoading(false);
        setError("You must be signed in to view team members.");
      }
    });
    return () => unsubscribe();
  }, []);
  
  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail) return;
    setInviting(true);
    setError(null);
    
    try {
      const user = auth.currentUser;
      if (!user) {
        throw new Error("You must be signed in to invite team members.");
      }

      const uid = user.uid;
      const userDocRef = doc(db, "users", uid);
      const userDoc = await getDoc(userDocRef);

      let existingMembers: any[] = [];
      if (userDoc.exists()) {
        const userData = userDoc.data();
        existingMembers = userData?.workspace?.members || [];
      }

      // Check if already invited
      if (existingMembers.some((m: any) => m.email === inviteEmail)) {
        throw new Error("This user has already been invited.");
      }

      // Create the new member entry
      const newMember = {
        id: `inv_${Date.now()}`,
        email: inviteEmail,
        name: inviteEmail,
        role: inviteRole,
        status: "Pending",
        joinedAt: new Date().toISOString(),
      };

      existingMembers.push(newMember);

      // Write to Firestore (merge so we don't overwrite other fields)
      await setDoc(userDocRef, {
        workspace: {
          members: existingMembers,
        },
      }, { merge: true });

      // Update local state
      setMembers([...members, newMember as TeamMember]);
      setInviteEmail("");
      setIsInviteModalOpen(false);
    } catch (err: any) {
      setError(err.message || "Failed to send invitation.");
    } finally {
      setInviting(false);
    }
  };
  
  const handleRemoveMember = async (id: string) => {
    try {
      const user = auth.currentUser;
      if (!user) return;

      const uid = user.uid;
      const userDocRef = doc(db, "users", uid);
      const userDoc = await getDoc(userDocRef);

      if (userDoc.exists()) {
        const userData = userDoc.data();
        const existingMembers: any[] = userData?.workspace?.members || [];
        const updatedMembers = existingMembers.filter((m: any) => m.id !== id);

        await setDoc(userDocRef, {
          workspace: {
            members: updatedMembers,
          },
        }, { merge: true });
      }

      setMembers(members.filter(m => m.id !== id));
    } catch (err: any) {
      setError(err.message || "Failed to remove member.");
    }
  };
  
  const handleRoleChange = async (id: string, newRole: 'Admin' | 'Editor' | 'Viewer') => {
    try {
      const user = auth.currentUser;
      if (!user) return;

      const uid = user.uid;
      const userDocRef = doc(db, "users", uid);
      const userDoc = await getDoc(userDocRef);

      if (userDoc.exists()) {
        const userData = userDoc.data();
        const existingMembers: any[] = userData?.workspace?.members || [];
        const updatedMembers = existingMembers.map((m: any) =>
          m.id === id ? { ...m, role: newRole } : m
        );

        await setDoc(userDocRef, {
          workspace: {
            members: updatedMembers,
          },
        }, { merge: true });
      }

      setMembers(members.map(m => m.id === id ? { ...m, role: newRole } : m));
    } catch (err: any) {
      setError(err.message || "Failed to update role.");
    }
  };

  const filteredMembers = members.filter(m => 
    m.name?.toLowerCase().includes(searchTerm.toLowerCase()) || 
    m.email?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-8">
      {/* Error banner */}
      {error && !loading && (
        <div className="rounded-2xl bg-amber-500/10 border border-amber-500/20 p-4 text-amber-100">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-300 mt-0.5" />
            <div>
              <p className="font-medium">Unable to load team members</p>
              <p className="text-sm text-amber-100/80">{error}</p>
              <button
                onClick={() => {
                  setError(null);
                  setLoading(true);
                  fetchTeamMembers();
                }}
                className="mt-3 inline-flex items-center gap-2 rounded-xl bg-amber-500/20 px-4 py-2 text-sm font-semibold text-amber-100 hover:bg-amber-500/30 transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl lg:text-4xl font-bold text-white">Team Members</h1>
          <p className="text-white/70 text-lg mt-1">Manage workspace access and roles</p>
        </div>
        <Button 
          onClick={() => setIsInviteModalOpen(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-600/20"
        >
          <UserPlus className="w-4 h-4 mr-2" />
          Invite Member
        </Button>
      </div>

      {/* Main Content */}
      <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
        {/* Toolbar */}
        <div className="p-4 border-b border-white/10 flex flex-col sm:flex-row gap-4 justify-between items-center bg-black/20">
          <div className="relative w-full sm:w-96">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
            <input
              type="text"
              placeholder="Search members by name or email..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-xl text-white focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>
          <div className="text-sm text-white/50">
            {members.length} {members.length === 1 ? 'member' : 'members'}
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/10 text-white/50 text-sm">
                <th className="px-6 py-4 font-medium">User</th>
                <th className="px-6 py-4 font-medium">Role</th>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading ? (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center text-white/50">
                    <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3 opacity-50" />
                    Loading members...
                  </td>
                </tr>
              ) : filteredMembers.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center text-white/50">
                    <Users className="w-12 h-12 mx-auto mb-3 opacity-20" />
                    No members found matching "{searchTerm}"
                  </td>
                </tr>
              ) : (
                filteredMembers.map((member) => (
                  <tr key={member.id} className="hover:bg-white/[0.02] transition-colors group">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-blue-600/20 text-blue-400 flex items-center justify-center font-bold border border-blue-500/20">
                          {member.name?.charAt(0) || member.email.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="text-white font-medium">{member.name || member.email}</div>
                          <div className="text-white/50 text-sm flex items-center gap-1">
                            <Mail className="w-3 h-3" /> {member.email}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button className="flex items-center gap-2 text-white/80 hover:text-white px-3 py-1.5 rounded-lg hover:bg-white/5 transition-colors">
                            <Shield className="w-4 h-4 text-blue-400" />
                            {member.role}
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="bg-black border border-white/10">
                          <DropdownMenuItem onClick={() => handleRoleChange(member.id, 'Admin')} className="text-white hover:bg-white/10 cursor-pointer">Admin</DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleRoleChange(member.id, 'Editor')} className="text-white hover:bg-white/10 cursor-pointer">Editor</DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleRoleChange(member.id, 'Viewer')} className="text-white hover:bg-white/10 cursor-pointer">Viewer</DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
                        member.status === 'Active' 
                          ? 'bg-green-500/10 text-green-400 border-green-500/20' 
                          : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      }`}>
                        {member.status === 'Active' ? <Check className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                        {member.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button className="p-2 text-white/40 hover:text-white hover:bg-white/10 rounded-lg transition-colors opacity-0 group-hover:opacity-100">
                            <MoreHorizontal className="w-5 h-5" />
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="bg-black border border-white/10">
                          {member.status === 'Pending' && (
                            <DropdownMenuItem className="text-white hover:bg-white/10 cursor-pointer">
                              Resend Invite
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem 
                            onClick={() => handleRemoveMember(member.id)}
                            className="text-red-400 hover:bg-red-400/10 hover:text-red-300 cursor-pointer"
                          >
                            Remove Member
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Invite Modal */}
      {isInviteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-[#0f0f13] border border-white/10 rounded-2xl w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between p-6 border-b border-white/10">
              <h2 className="text-xl font-semibold text-white">Invite Team Member</h2>
              <button 
                onClick={() => setIsInviteModalOpen(false)}
                className="text-white/40 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleInvite} className="p-6 space-y-4">
              {error && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                  {error}
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">Email Address</label>
                <input
                  type="email"
                  required
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="colleague@company.com"
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-white focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">Role</label>
                <div className="grid grid-cols-3 gap-2">
                  {['Admin', 'Editor', 'Viewer'].map((role) => (
                    <button
                      key={role}
                      type="button"
                      onClick={() => setInviteRole(role as any)}
                      className={`px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                        inviteRole === role 
                          ? 'bg-blue-600/20 border-blue-500 text-blue-400' 
                          : 'bg-white/5 border-transparent text-white/60 hover:bg-white/10 hover:text-white'
                      }`}
                    >
                      {role}
                    </button>
                  ))}
                </div>
              </div>
              <div className="pt-4 flex gap-3">
                <Button 
                  type="button" 
                  onClick={() => setIsInviteModalOpen(false)}
                  variant="ghost" 
                  className="flex-1 text-white/70 hover:text-white hover:bg-white/10"
                >
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  disabled={inviting}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50 flex items-center justify-center"
                >
                  {inviting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  {inviting ? 'Sending...' : 'Send Invite'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
