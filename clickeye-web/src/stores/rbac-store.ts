import { create } from "zustand";

import type { SystemRole } from "@/lib/api-client";

interface RBACState {
  permissions: string[];
  systemRole: SystemRole | null;
  loaded: boolean;
}

interface RBACActions {
  setPermissions: (permissions: string[], systemRole: SystemRole) => void;
  hasPermission: (permission: string) => boolean;
  isAdmin: () => boolean;
  isSuperadmin: () => boolean;
  reset: () => void;
}

export const useRBACStore = create<RBACState & RBACActions>((set, get) => ({
  permissions: [],
  systemRole: null,
  loaded: false,

  setPermissions: (permissions, systemRole) =>
    set({ permissions, systemRole, loaded: true }),

  hasPermission: (permission) => get().permissions.includes(permission),

  isAdmin: () => {
    const role = get().systemRole;
    return role === "superadmin" || role === "admin";
  },

  isSuperadmin: () => get().systemRole === "superadmin",

  reset: () => set({ permissions: [], systemRole: null, loaded: false }),
}));
