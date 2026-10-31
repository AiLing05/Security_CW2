export async function fetchProtectedFile(url, token) {
  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error(
      response.status === 401
        ? "Please log in to access this file."
        : response.status === 403
        ? "You do not have permission to access this file."
        : "Unable to load the file."
    );
  }

  return URL.createObjectURL(await response.blob());
}

export async function openProtectedFile(url, token) {
  const objectUrl = await fetchProtectedFile(url, token);

  const link = document.createElement("a");
  link.href = objectUrl;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  document.body.appendChild(link);
  link.click();
  link.remove();
}
