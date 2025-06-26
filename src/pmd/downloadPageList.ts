import { DOMParser, Element } from "https://deno.land/x/deno_dom/deno-dom-wasm.ts";
import { ensureDir } from "https://deno.land/std@0.192.0/fs/ensure_dir.ts"; // Using a pinned version for stability

async function fetchAndParse(url: string): Promise<string[]> {
  try {
    console.log(`Fetching URL list from: ${url}`);
    const response = await fetch(url);
    if (!response.ok) {
      console.error(`Error fetching ${url}: ${response.status} ${response.statusText}`);
      return [];
    }
    const html = await response.text();
    const doc = new DOMParser().parseFromString(html, "text/html");
    if (!doc) {
        console.error("Failed to parse HTML document from " + url);
        return [];
    }

    const links: string[] = [];
    // querySelectorAll expects string selectors.
    // Python: soup.select("#main table tr td:first-child a")
    const elements = doc.querySelectorAll("#main table tr td:first-child a");

    elements.forEach(elementNode => {
      // Ensure elementNode is an Element and has getAttribute method
      if (elementNode instanceof Element) {
        const href = elementNode.getAttribute("href");
        if (href) {
          // Python: e['href'].split("=")[0] + "=" + quote(e['href'].split("=")[1], safe='/()')
          // JS equivalent of quote with safe characters: encodeURIComponent, then selectively decode.
          // However, the URLs on aonprd.com seem to be already reasonably encoded or don't need complex quoting.
          // Example: MonsterDisplay.aspx?ItemName=Wolf
          // Example: MonsterDisplay.aspx?ItemName=Dragon%2C%20Faerie
          // The Python quote(..., safe='/()') might be to prevent over-encoding of already %-encoded parts,
          // or to ensure specific characters like parentheses are not encoded if they are part of the name.
          // Modern URLs handle many characters directly. Let's try a simpler approach first.
          // The original Python code's specific quoting `quote(e['href'].split("=")[1], safe='/()')`
          // suggests that the `ItemName` parameter might contain characters that need careful encoding,
          // but parentheses and slashes should be preserved if they are part of the name.
          // `encodeURIComponent` would encode those. A direct href is likely fine.
          let fullUrl = href;
          if (!fullUrl.toLowerCase().startsWith("https://aonprd.com/")) {
            if (fullUrl.startsWith("/")) {
                fullUrl = "https://aonprd.com" + fullUrl;
            } else {
                fullUrl = "https://aonprd.com/" + fullUrl;
            }
          }
          // The original also did specific quoting for the query parameter part.
          // Let's try to replicate that logic carefully.
          const parts = href.split("=");
          if (parts.length > 1) {
            const base = parts[0];
            const itemVal = parts.slice(1).join("="); // Rejoin if value had '='
            // encodeURIComponent encodes '(', ')', '/'. Python's quote with safe='/()' does not.
            // For robustness, let's assume the hrefs are mostly fine as-is from the site.
            // If specific encoding is needed, it's often better to construct URLs with URLSearchParams.
            // For now, let's use the href directly and normalize the domain.
            // The original Python did: quote(e['href'].split("=")[1], safe='/()')
            // This means it only encoded the value part of the query string.
            // Let's try to replicate:
             const baseUrlParts = fullUrl.split('?');
             if (baseUrlParts.length > 1) {
                const queryParams = new URLSearchParams(baseUrlParts[1]);
                const itemName = queryParams.get("ItemName");
                if (itemName) {
                    // A direct translation of `quote(itemName, safe='/()')` is tricky.
                    // `encodeURIComponent` is too aggressive.
                    // A simpler approach might be to just ensure the URL is valid.
                    // For now, using the href as extracted and prefixing domain if needed.
                    // The critical part `quote(e['href'].split("=")[1], safe='/()')` likely handled spaces to %20
                    // and other special chars, but kept / and () as is.
                    // Most modern fetch implementations handle URLs well.
                    // Let's keep `fullUrl` as constructed from `href` and domain prefixing.
                    // If issues arise, this part needs a closer look at what `quote` with `safe` did.
                    // A common need is to ensure spaces are %20, which `new URL()` constructor does.
                    try {
                        const validatedUrl = new URL(fullUrl);
                        links.push(validatedUrl.href);
                    } catch (urlError) {
                        console.warn(`Skipping invalid URL '${fullUrl}': ${urlError.message}`);
                    }

                } else {
                     links.push(fullUrl); // No ItemName param, take as is
                }
             } else {
                 links.push(fullUrl); // No query string
             }
          } else {
             links.push(fullUrl); // No query string with '='
          }
        }
      }
    });
    return links;
  } catch (error) {
    console.error(`Failed to process ${url}: ${error}`);
    if (error.stack) console.error(error.stack);
    return [];
  }
}

async function main() {
  const args = Deno.args;
  const defaultUrls = [
    "https://aonprd.com/Monsters.aspx?Letter=All",
    "https://aonprd.com/NPCs.aspx?SubGroup=All",
    "https://aonprd.com/MythicMonsters.aspx?Letter=All"
  ];
  const pageListUrls = args.length > 0 ? args : defaultUrls;
  const outfilePath = "pmd_data/urls.txt"; // Changed output path

  await ensureDir("pmd_data"); // Ensure pmd_data directory exists

  let allUrls: string[] = [];
  for (const url of pageListUrls) {
    const urlsFromPage = await fetchAndParse(url);
    allUrls.push(...urlsFromPage);
  }

  // Remove duplicates and sort
  const uniqueSortedUrls = [...new Set(allUrls)].sort();

  try {
    await Deno.writeTextFile(outfilePath, uniqueSortedUrls.join("\n"));
    console.log(`Successfully wrote ${uniqueSortedUrls.length} URLs to ${outfilePath}`);
  } catch (error) {
    console.error(`Error writing to ${outfilePath}: ${error}`);
  }
}

if (import.meta.main) {
  main();
}
