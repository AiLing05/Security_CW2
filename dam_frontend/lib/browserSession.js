let currentUser = null;

export function setSessionUser(user) {
  currentUser = user;
  if (typeof window !== "undefined") {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    if (user) {
      localStorage.setItem("username", user.username);
      localStorage.setItem("role", user.role);
    } else {
      localStorage.removeItem("username");
      localStorage.removeItem("role");
    }
  }
}

export function isAuthenticated() {
  return currentUser !== null;
}

export function getSessionUser() {
  return currentUser;
}
