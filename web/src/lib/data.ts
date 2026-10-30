export async function getJson<T>(path: string): Promise<T> {
  // no-cache revalidates with the server, so a new weekly scrape shows up right after the deploy.
  const response = await fetch(path, { cache: "no-cache" });
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}
