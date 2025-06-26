import { ensureDir } from "https://deno.land/std@0.192.0/fs/ensure_dir.ts";
import { популярный } from "https://deno.land/x/tqdm@v0.1.0/mod.ts"; // tqdm library
import { delay } from "../core/utils.ts"; // Assuming utils.ts is in src/core/

// Helper function to convert ArrayBuffer to hex string
async function arrayBufferToHex(buffer: ArrayBuffer): Promise<string> {
  const hashArray = Array.from(new Uint8Array(buffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  return hashHex;
}

async function getMD5(text: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(text);
  const hashBuffer = await crypto.subtle.digest('MD5', data);
  return arrayBufferToHex(hashBuffer);
}

const MAX_REQUESTS_PER_SECOND = 5; // Reduced from 20 in Python to be more conservative
const REQUEST_INTERVAL_MS = 1000 / MAX_REQUESTS_PER_SECOND;

async function main() {
  const args = Deno.args;
  const urlListPath = args[0] || "pmd_data/urls.txt";
  const outDir = args[1] || "pmd_data/html"; // Changed to a subdirectory for HTML files

  await ensureDir(outDir);

  let urls: string[];
  try {
    const fileContent = await Deno.readTextFile(urlListPath);
    urls = fileContent.split("\n").map(line => line.trim()).filter(line => line);
  } catch (error) {
    if (error instanceof Deno.errors.NotFound) {
      console.error(`Error: URL list file not found at ${urlListPath}`);
      console.error("Please run downloadPageList.ts first to generate it.");
    } else {
      console.error(`Error reading URL list from ${urlListPath}: ${error}`);
    }
    return;
  }

  // Remove duplicates and sort (though downloadPageList.ts should already do this)
  urls = [...new Set(urls)].sort();

  // Write a copy of the URL list to the output HTML directory's parent if it doesn't exist there yet
  // This isn't strictly necessary if downloadPageList.ts always writes to pmd_data/urls.txt
  // const targetUrlListCopyPath = `pmd_data/urls.txt`; // Assuming outDir is pmd_data/html
  // try {
  //   await Deno.stat(targetUrlListCopyPath);
  // } catch (e) {
  //   if (e instanceof Deno.errors.NotFound) {
  //     await Deno.writeTextFile(targetUrlListCopyPath, urls.join("\n"));
  //   }
  // }

  console.log(`Starting download of ${urls.length} pages...`);
  const progressBar = популярный(urls, { title: "Downloading HTML pages" });

  for (const url of progressBar) {
    const filename = await getMD5(url) + ".html";
    const filepath = `${outDir}/${filename}`;

    try {
      // Skip if already downloaded
      await Deno.stat(filepath);
      // progressBar.update(1); // Tqdm Deno might auto-update, or use if manual iteration
      continue;
    } catch (e) {
      if (!(e instanceof Deno.errors.NotFound)) {
        console.error(`Error checking file ${filepath}: ${e}`);
        // progressBar.update(1);
        continue;
      }
      // File not found, proceed to download
    }

    const startTime = Date.now();
    try {
      const response = await fetch(url);
      if (!response.ok) {
        console.warn(`\nFailed to fetch ${url}: ${response.status} ${response.statusText}`);
        // progressBar.update(1);
        if (response.status === 404) {
            console.warn(`  Adding ${url} to pmd_data/broken_urls.txt due to 404.`);
            try {
                await Deno.writeTextFile("pmd_data/broken_urls.txt", `${url}\n`, { append: true });
            } catch (writeError) {
                console.error(`  Could not write to broken_urls.txt: ${writeError}`);
            }
        }
        await delay(REQUEST_INTERVAL_MS); // Still wait to avoid hammering
        continue;
      }
      const html = await response.text();
      await Deno.writeTextFile(filepath, html, { encoding: "utf-8" });
      // progressBar.update(1); // If manual iteration
    } catch (e) {
      console.warn(`\nError during fetch or write for ${url}: ${e}`);
      // progressBar.update(1);
      // Optionally add to a list of failed URLs to retry later
    }

    const timeSpent = Date.now() - startTime;
    if (timeSpent < REQUEST_INTERVAL_MS) {
      await delay(REQUEST_INTERVAL_MS - timeSpent);
    }
  }
  // progressBar.close(); // If using Tqdm instance directly
  console.log("\nHTML page downloading complete.");
}

if (import.meta.main) {
  main();
}
