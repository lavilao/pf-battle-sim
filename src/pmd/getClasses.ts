import { DOMParser, Element } from "https://deno.land/x/deno_dom/deno-dom-wasm.ts";
import { популярный } from "https://deno.land/x/tqdm@v0.1.0/mod.ts";
import { delay } from "../core/utils.ts";
import { ensureDir } from "https://deno.land/std@0.192.0/fs/ensure_dir.ts";

const MAX_REQUESTS_PER_SECOND = 5; // Be polite
const REQUEST_INTERVAL_MS = 1000 / MAX_REQUESTS_PER_SECOND;

interface ClassEntry {
  name: string;
  url: string;
}

async function fetchPage(url: string): Promise<string | null> {
  try {
    const response = await fetch(url);
    if (!response.ok) {
      console.warn(`Error fetching ${url}: ${response.status} ${response.statusText}`);
      return null;
    }
    return await response.text();
  } catch (error) {
    console.error(`Failed to fetch ${url}: ${error}`);
    return null;
  }
}

async function main() {
  const urlClasses = "https://aonprd.com/Classes.aspx";
  const urlPrestige = "https://aonprd.com/PrestigeClasses.aspx";
  const urlMythic = "https://aonprd.com/MythicPaths.aspx";
  const outfilePath = "pmd_data/class_hds.json";

  const classHitDice: Record<string, number | null> = {};

  await ensureDir("pmd_data");

  const allClassEntries: ClassEntry[] = [];

  // Regular Classes
  console.log("Fetching regular class list...");
  let html = await fetchPage(urlClasses);
  if (html) {
    let doc = new DOMParser().parseFromString(html, "text/html");
    if (doc) {
        // Python: soup.select("#MainContent_AllClassLabel a")
        doc.querySelectorAll("#MainContent_AllClassLabel a").forEach(node => {
            if (node instanceof Element) {
                const name = node.textContent.trim();
                let href = node.getAttribute("href") || "";
                if (!href.toLowerCase().startsWith("https://aonprd.com/")) {
                    href = "https://aonprd.com/" + href.replace(/^\//, "");
                }
                if (name && href) allClassEntries.push({ name, url: href });
            }
        });
    }
  }

  // Prestige Classes
  console.log("Fetching prestige class list...");
  html = await fetchPage(urlPrestige);
  if (html) {
    let doc = new DOMParser().parseFromString(html, "text/html");
    if (doc) {
        // Python: soup.select("#MainContent_GridViewPrestigeClasses td:first-child a")
        doc.querySelectorAll("#MainContent_GridViewPrestigeClasses td:first-child a").forEach(node => {
            if (node instanceof Element) {
                const name = node.textContent.trim();
                let href = node.getAttribute("href") || "";
                 if (!href.toLowerCase().startsWith("https://aonprd.com/")) {
                    href = "https://aonprd.com/" + href.replace(/^\//, "");
                }
                if (name && href) allClassEntries.push({ name, url: href });
            }
        });
    }
  }

  console.log(`Found ${allClassEntries.length} classes/prestige classes. Fetching details...`);
  const progressBar = популярный(allClassEntries, { title: "Fetching class Hit Dice" });

  for (const entry of progressBar) {
    const { name, url } = entry;
    if (name === "Familiar") { // Special case
      classHitDice[name] = null; // No hit die
      await delay(REQUEST_INTERVAL_MS);
      continue;
    }

    const classPageHtml = await fetchPage(url);
    if (!classPageHtml) {
      console.warn(`Could not fetch page for class: ${name} (${url})`);
      await delay(REQUEST_INTERVAL_MS); // still delay
      continue;
    }

    const classDoc = new DOMParser().parseFromString(classPageHtml, "text/html");
    if (!classDoc) {
        console.warn(`Could not parse page for class: ${name} (${url})`);
        await delay(REQUEST_INTERVAL_MS);
        continue;
    }

    let foundHd = false;
    // Normal classes selector: #MainContent_DataListTypes_LabelName_0
    // Then text search for "Hit Die: dX."
    const mainContentLabel = classDoc.querySelector("#MainContent_DataListTypes_LabelName_0");
    if (mainContentLabel) {
        const textContent = mainContentLabel.textContent || "";
        const match = textContent.match(/Hit Die: d(\d+)\./);
        if (match && match[1]) {
            classHitDice[name] = parseInt(match[1], 10);
            foundHd = true;
        }
    }

    // Weird classes (e.g. Companion) selector: find_all('b', string="HD") ... parent is span ... nextSibling text match (dX)
    if (!foundHd) {
        const hdBoldElements = classDoc.querySelectorAll("b");
        for (const bElement of hdBoldElements) {
            if (bElement instanceof Element && bElement.textContent.trim() === "HD") {
                if (bElement.parentElement && bElement.parentElement.tagName === "SPAN") { // Check parent is span
                    const nextSibling = bElement.nextSibling;
                    if (nextSibling && nextSibling.nodeType === nextSibling.TEXT_NODE) { // TEXT_NODE is 3
                        const textContent = nextSibling.textContent || "";
                        const match = textContent.match(/\(d(\d+)\)/);
                        if (match && match[1]) {
                            classHitDice[name] = parseInt(match[1], 10);
                            foundHd = true;
                            break;
                        }
                    }
                }
            }
        }
    }
    if (!foundHd) {
        console.warn(`Could not find Hit Die for class: ${name} (${url})`);
    }
    await delay(REQUEST_INTERVAL_MS);
  }

  // Mythic Paths
  console.log("Fetching mythic path list...");
  html = await fetchPage(urlMythic);
  if (html) {
    let doc = new DOMParser().parseFromString(html, "text/html");
    if (doc) {
        // Python: soup.select("#main > h1 a")
        doc.querySelectorAll("#main > h1 a").forEach(node => {
            if (node instanceof Element) {
                const name = node.textContent.trim();
                if (name) classHitDice[name] = 0; // Mythic paths give no HD, encoded as d0
            }
        });
    }
  }

  // Add manual entries
  if (classHitDice["Kineticist"] !== undefined) {
    classHitDice["Geokineticist"] = classHitDice["Kineticist"];
    classHitDice["Hydrokineticist"] = classHitDice["Kineticist"];
  } else {
    console.warn("Kineticist HD not found, cannot set for Geokineticist/Hydrokineticist.");
  }
  if (classHitDice["Wizard"] !== undefined) {
    classHitDice["Abjurer"] = classHitDice["Wizard"];
    classHitDice["Conjurer"] = classHitDice["Wizard"];
    classHitDice["Diviner"] = classHitDice["Wizard"];
    classHitDice["Enchanter"] = classHitDice["Wizard"];
    classHitDice["Evoker"] = classHitDice["Wizard"];
    classHitDice["Illusionist"] = classHitDice["Wizard"];
    classHitDice["Necromancer"] = classHitDice["Wizard"];
    classHitDice["Transmuter"] = classHitDice["Wizard"];
  } else {
    console.warn("Wizard HD not found, cannot set for specialist wizards.");
  }

  try {
    await Deno.writeTextFile(outfilePath, JSON.stringify(classHitDice, null, 2));
    console.log(`\nSuccessfully wrote class Hit Dice data to ${outfilePath}`);
  } catch (error) {
    console.error(`\nError writing to ${outfilePath}: ${error}`);
  }
}

if (import.meta.main) {
  main();
}
